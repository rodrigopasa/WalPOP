#!/usr/bin/env python3
"""
Walpop v2.0 — Gerenciador de Wallpapers Animados para Pop!_OS 24.04
Usa mpvpaper (Wayland) para aplicar wallpapers de vídeo.
Interface em português brasileiro com customtkinter (tema dark).
"""

import os
import sys
import json
import shutil
import hashlib
import logging
import subprocess
import threading
import re
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

# ─── Constantes ──────────────────────────────────────────────────────────────

APP_NAME = "Walpop"
APP_VERSION = "2.0"
CONFIG_DIR = os.path.expanduser("~/.config/walpop")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "walpop.log")
THUMBS_DIR = os.path.join(CONFIG_DIR, "thumbs")

STEAM_WORKSHOP_PATHS = [
    os.path.expanduser("~/.local/share/Steam/steamapps/workshop/content/431960"),
    os.path.expanduser("~/.steam/debian-installation/steamapps/workshop/content/431960"),
]

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv"}
FPS_VALUES = [10, 15, 24, 30, 60]

DEFAULT_CONFIG = {
    "fps": 30,
    "custom_folder": "",
    "last_wallpaper": "",
    "autostart": False,
}

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "walpop-daemon.desktop")

# ─── Logging ─────────────────────────────────────────────────────────────────

def setup_logging():
    """Configura logging para arquivo e console."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

# ─── Utilitários ─────────────────────────────────────────────────────────────

def check_command(name):
    """Retorna True se o comando existe no PATH."""
    return shutil.which(name) is not None

def truncate_text(text, max_length=40):
    """Trunca texto adicionando '...' se necessário."""
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text

# ─── ConfigManager ───────────────────────────────────────────────────────────

class ConfigManager:
    """Gerencia configuração persistente em JSON."""

    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(THUMBS_DIR, exist_ok=True)
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.data.update(saved)
                logging.info("Config carregada: %s", CONFIG_FILE)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning("Falha ao ler config, usando padrão: %s", e)

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logging.error("Falha ao salvar config: %s", e)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

# ─── Wallpaper (model) ───────────────────────────────────────────────────────

class Wallpaper:
    """Modelo para um wallpaper de vídeo."""

    def __init__(self, title, file_path, preview_path, source):
        self.title = title
        self.file_path = file_path
        self.preview_path = preview_path  # Pode ser None
        self.source = source  # "steam" ou "custom"

    @property
    def source_tag(self):
        return "[Steam]" if self.source == "steam" else "[Custom]"

# ─── WallpaperScanner ─────────────────────────────────────────────────────────

class WallpaperScanner:
    """Escaneia wallpapers de vídeo do Steam Workshop e pasta customizada."""

    @staticmethod
    def scan_steam():
        """Escaneia as pastas do Steam Workshop."""
        wallpapers = []
        workshop_path = None

        for path in STEAM_WORKSHOP_PATHS:
            if os.path.isdir(path):
                workshop_path = path
                break

        if not workshop_path:
            logging.info("Pasta do Steam Workshop não encontrada.")
            return wallpapers

        logging.info("Escaneando Steam Workshop: %s", workshop_path)

        for folder_name in os.listdir(workshop_path):
            folder_path = os.path.join(workshop_path, folder_name)
            if not os.path.isdir(folder_path):
                continue

            project_json = os.path.join(folder_path, "project.json")
            if not os.path.exists(project_json):
                continue

            try:
                with open(project_json, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Ignorar scene e web
                wp_type = data.get("type", "").lower()
                if wp_type in ("scene", "web"):
                    continue

                title = data.get("title", f"Sem título ({folder_name})")
                file_name = data.get("file", "")
                if not file_name:
                    continue

                ext = os.path.splitext(file_name)[1].lower()
                if ext not in VIDEO_EXTENSIONS:
                    continue

                file_path = os.path.join(folder_path, file_name)
                if not os.path.exists(file_path):
                    continue

                # Buscar preview existente
                preview_path = None
                for preview_name in ("preview.jpg", "preview.png", "preview.gif", "preview.jpeg"):
                    candidate = os.path.join(folder_path, preview_name)
                    if os.path.exists(candidate):
                        preview_path = candidate
                        break

                wallpapers.append(Wallpaper(title, file_path, preview_path, "steam"))

            except (json.JSONDecodeError, IOError) as e:
                logging.warning("Erro ao ler %s: %s", project_json, e)
                continue

        logging.info("Steam: %d wallpapers encontrados.", len(wallpapers))
        return wallpapers

    @staticmethod
    def scan_custom(folder_path):
        """Escaneia todos os vídeos de uma pasta customizada."""
        wallpapers = []

        if not folder_path or not os.path.isdir(folder_path):
            return wallpapers

        logging.info("Escaneando pasta customizada: %s", folder_path)

        for entry in os.listdir(folder_path):
            full_path = os.path.join(folder_path, entry)
            if not os.path.isfile(full_path):
                continue

            ext = os.path.splitext(entry)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue

            title = os.path.splitext(entry)[0]
            wallpapers.append(Wallpaper(title, full_path, None, "custom"))

        logging.info("Custom: %d wallpapers encontrados.", len(wallpapers))
        return wallpapers

    @classmethod
    def scan_all(cls, custom_folder):
        """Combina Steam + Custom e ordena por nome."""
        all_wp = cls.scan_steam() + cls.scan_custom(custom_folder)
        all_wp.sort(key=lambda w: w.title.lower())
        return all_wp

# ─── ThumbnailCache ──────────────────────────────────────────────────────────

class ThumbnailCache:
    """Gera e armazena cache de thumbnails via ffmpeg."""

    HAS_FFMPEG = check_command("ffmpeg")

    @classmethod
    def get_thumb_path(cls, video_path):
        """Retorna o caminho do thumbnail em cache."""
        video_hash = hashlib.md5(video_path.encode()).hexdigest()
        return os.path.join(THUMBS_DIR, f"{video_hash}.jpg")

    @classmethod
    def get_or_create(cls, wallpaper):
        """Retorna o caminho do thumbnail, gerando se necessário."""
        # Se já tem preview (Steam), usar direto
        if wallpaper.preview_path and os.path.exists(wallpaper.preview_path):
            return wallpaper.preview_path

        if not cls.HAS_FFMPEG:
            return None

        thumb_path = cls.get_thumb_path(wallpaper.file_path)
        if os.path.exists(thumb_path):
            return thumb_path

        # Gerar thumbnail
        try:
            subprocess.run(
                [
                    "ffmpeg", "-i", wallpaper.file_path,
                    "-ss", "00:00:01", "-vframes", "1",
                    "-y", thumb_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            if os.path.exists(thumb_path):
                logging.info("Thumbnail gerado: %s", thumb_path)
                return thumb_path
        except Exception as e:
            logging.warning("Falha ao gerar thumbnail para %s: %s", wallpaper.file_path, e)

        return None

# ─── WallpaperManager ────────────────────────────────────────────────────────

class WallpaperManager:
    """Aplica wallpapers usando mpvpaper."""

    HAS_MPVPAPER = check_command("mpvpaper")

    @classmethod
    def apply(cls, video_path, fps=30):
        """Mata mpvpaper anterior e aplica novo wallpaper."""
        if not cls.HAS_MPVPAPER:
            logging.error("mpvpaper não está instalado.")
            return False

        try:
            subprocess.run(["pkill", "mpvpaper"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time
            time.sleep(0.3)

            cmd = [
                "mpvpaper",
                "-o", f"loop --vf=fps={fps}",
                "*",
                video_path,
            ]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logging.info("Wallpaper aplicado: %s (FPS: %d)", video_path, fps)
            return True

        except Exception as e:
            logging.error("Erro ao aplicar wallpaper: %s", e)
            return False

# ─── VideoOptimizer ──────────────────────────────────────────────────────────

class VideoOptimizer:
    """Otimiza vídeos usando ffmpeg em thread separada."""

    HAS_FFMPEG = check_command("ffmpeg")

    @classmethod
    def optimize(cls, input_path, output_path, progress_callback=None, done_callback=None):
        """Roda otimização em thread separada. Callbacks executados na thread."""

        def _run():
            try:
                # Pegar duração total para calcular progresso
                probe = subprocess.run(
                    [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        input_path,
                    ],
                    capture_output=True, text=True, timeout=10,
                )
                total_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", "scale=1280:720",
                    "-c:v", "libx264",
                    "-crf", "28",
                    "-an",
                    "-progress", "pipe:1",
                    "-y", output_path,
                ]

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )

                for line in process.stdout:
                    if line.startswith("out_time_ms="):
                        try:
                            time_ms = int(line.split("=")[1].strip())
                            time_s = time_ms / 1_000_000
                            if total_duration > 0 and progress_callback:
                                pct = min(time_s / total_duration, 1.0)
                                progress_callback(pct)
                        except (ValueError, IndexError):
                            pass

                process.wait()

                if process.returncode == 0:
                    logging.info("Vídeo otimizado: %s", output_path)
                    if done_callback:
                        done_callback(True)
                else:
                    logging.error("ffmpeg retornou código %d", process.returncode)
                    if done_callback:
                        done_callback(False)

            except Exception as e:
                logging.error("Erro na otimização: %s", e)
                if done_callback:
                    done_callback(False)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

# ─── Autostart ───────────────────────────────────────────────────────────────

class AutostartManager:
    """Gerencia autostart via arquivo .desktop."""

    @staticmethod
    def enable():
        """Cria arquivo de autostart."""
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        script_path = os.path.abspath(__file__)
        content = f"""[Desktop Entry]
Type=Application
Name=Walpop
Exec=python3 {script_path} --autostart
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        try:
            with open(AUTOSTART_FILE, "w") as f:
                f.write(content)
            logging.info("Autostart ativado: %s", AUTOSTART_FILE)
        except IOError as e:
            logging.error("Falha ao criar autostart: %s", e)

    @staticmethod
    def disable():
        """Remove arquivo de autostart."""
        try:
            if os.path.exists(AUTOSTART_FILE):
                os.remove(AUTOSTART_FILE)
                logging.info("Autostart desativado.")
        except IOError as e:
            logging.error("Falha ao remover autostart: %s", e)

# ─── UI Principal ─────────────────────────────────────────────────────────────

class WalpopApp(ctk.CTk):
    """Interface gráfica principal do Walpop."""

    THUMB_SIZE = (80, 45)  # 16:9 ish

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.wallpapers = []
        self.thumb_refs = []  # Manter referências para GC

        # Janela
        self.title(f"🎬 {APP_NAME}")
        self.geometry("780x650")
        self.minsize(640, 500)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Checar dependências
        self.has_mpvpaper = WallpaperManager.HAS_MPVPAPER
        self.has_ffmpeg = ThumbnailCache.HAS_FFMPEG

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Carregar wallpapers na inicialização
        self.after(200, self._refresh_list)

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # row 2 = lista scrollable

        # ── Header ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=f"🎬 {APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        # ── Avisos de dependência ────────────────────────────────────────
        if not self.has_mpvpaper:
            warn = ctk.CTkLabel(
                self,
                text="⚠️  mpvpaper não encontrado! Instale com: sudo apt install mpvpaper",
                text_color="#ff6b6b",
                font=ctk.CTkFont(size=12),
            )
            warn.grid(row=0, column=0, sticky="ew", padx=16, pady=(44, 0))

        if not self.has_ffmpeg:
            warn2 = ctk.CTkLabel(
                self,
                text="⚠️  ffmpeg não encontrado! Botão Otimizar desabilitado.",
                text_color="#ffa94d",
                font=ctk.CTkFont(size=12),
            )
            warn2.grid(row=0, column=0, sticky="ew", padx=16, pady=(62, 0))

        # ── Pasta customizada ─────────────────────────────────────────────
        custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 4))
        custom_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            custom_frame, text="Pasta customizada:", font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.custom_entry = ctk.CTkEntry(
            custom_frame, placeholder_text="/home/usuario/Wallpapers"
        )
        self.custom_entry.grid(row=0, column=1, sticky="ew")

        saved_folder = self.config.get("custom_folder", "")
        if saved_folder:
            self.custom_entry.insert(0, saved_folder)

        ctk.CTkButton(
            custom_frame, text="📁", width=40,
            command=self._browse_custom_folder,
        ).grid(row=0, column=2, padx=(6, 0))

        # ── Lista de wallpapers (scrollable) ────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Wallpapers")
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 6))
        self.list_frame.grid_columnconfigure(1, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="Nenhum wallpaper encontrado",
            text_color="gray",
            font=ctk.CTkFont(size=14),
        )

        # ── Barra de progresso (otimização) ──────────────────────────────
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 2))
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.progress_label.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        self.progress_bar.set(0)
        self.progress_frame.grid_remove()  # Oculto por padrão

        # ── Controles inferiores ─────────────────────────────────────────
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=4, column=0, sticky="ew", padx=16, pady=(4, 12))
        controls.grid_columnconfigure(1, weight=1)

        # FPS slider
        fps_frame = ctk.CTkFrame(controls, fg_color="transparent")
        fps_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        fps_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fps_frame, text="FPS:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        self.fps_slider = ctk.CTkSlider(
            fps_frame, from_=0, to=4, number_of_steps=4,
            command=self._on_fps_change,
        )
        self.fps_slider.grid(row=0, column=1, sticky="ew")

        # Posicionar slider no valor salvo
        saved_fps = self.config.get("fps", 30)
        idx = FPS_VALUES.index(saved_fps) if saved_fps in FPS_VALUES else 3
        self.fps_slider.set(idx)

        self.fps_label = ctk.CTkLabel(
            fps_frame, text=f"{saved_fps} fps",
            font=ctk.CTkFont(size=13, weight="bold"), width=60,
        )
        self.fps_label.grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(
            fps_frame,
            text="FPS menor = menos consumo de CPU",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        ).grid(row=1, column=0, columnspan=3, sticky="w")

        # Autostart toggle
        self.autostart_var = ctk.BooleanVar(value=self.config.get("autostart", False))
        self.autostart_switch = ctk.CTkSwitch(
            controls,
            text="Iniciar com o sistema",
            variable=self.autostart_var,
            command=self._on_autostart_toggle,
            font=ctk.CTkFont(size=13),
        )
        self.autostart_switch.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Botão atualizar
        ctk.CTkButton(
            controls,
            text="🔄 Atualizar lista",
            command=self._refresh_list,
            width=140,
        ).grid(row=1, column=2, sticky="e", pady=(4, 0))

        # Status bar
        self.status_label = ctk.CTkLabel(
            self, text="Pronto", anchor="w",
            font=ctk.CTkFont(size=11), text_color="gray",
        )
        self.status_label.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 6))

    # ── Ações ─────────────────────────────────────────────────────────────

    def _browse_custom_folder(self):
        folder = filedialog.askdirectory(title="Escolha a pasta de wallpapers")
        if folder:
            self.custom_entry.delete(0, "end")
            self.custom_entry.insert(0, folder)
            self.config.set("custom_folder", folder)
            self._refresh_list()

    def _get_current_fps(self):
        idx = int(round(self.fps_slider.get()))
        return FPS_VALUES[idx]

    def _on_fps_change(self, value):
        fps = self._get_current_fps()
        self.fps_label.configure(text=f"{fps} fps")
        self.config.set("fps", fps)

    def _on_autostart_toggle(self):
        enabled = self.autostart_var.get()
        self.config.set("autostart", enabled)
        if enabled:
            AutostartManager.enable()
        else:
            AutostartManager.disable()

    def _set_status(self, text):
        self.status_label.configure(text=text)

    # ── Lista de wallpapers ──────────────────────────────────────────────

    def _refresh_list(self):
        self._set_status("Escaneando wallpapers...")
        self.update()

        # Limpar lista
        for child in self.list_frame.winfo_children():
            if child != self.empty_label:
                child.destroy()
        self.thumb_refs.clear()

        custom_folder = self.custom_entry.get().strip()
        if custom_folder:
            self.config.set("custom_folder", custom_folder)

        self.wallpapers = WallpaperScanner.scan_all(custom_folder)

        if not self.wallpapers:
            self.empty_label.grid(row=0, column=0, columnspan=4, pady=40)
            self._set_status("Nenhum wallpaper encontrado")
            return

        self.empty_label.grid_remove()

        for i, wp in enumerate(self.wallpapers):
            self._add_wallpaper_row(i, wp)

        self._set_status(f"{len(self.wallpapers)} wallpapers encontrados")

    def _add_wallpaper_row(self, row_idx, wp):
        """Adiciona uma linha na lista para um wallpaper."""
        row_frame = ctk.CTkFrame(self.list_frame, corner_radius=8)
        row_frame.grid(row=row_idx, column=0, sticky="ew", padx=4, pady=3)
        row_frame.grid_columnconfigure(1, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Thumbnail
        thumb_image = self._load_thumbnail(wp)
        thumb_label = ctk.CTkLabel(row_frame, text="", image=thumb_image, width=80, height=45)
        thumb_label.grid(row=0, column=0, rowspan=2, padx=(8, 10), pady=6)

        # Nome + tag
        tag_color = "#63b3ed" if wp.source == "steam" else "#68d391"
        name_text = truncate_text(wp.title, 38)
        name_label = ctk.CTkLabel(
            row_frame,
            text=f"{name_text}  ",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        name_label.grid(row=0, column=1, sticky="w", pady=(8, 0))

        tag_label = ctk.CTkLabel(
            row_frame,
            text=wp.source_tag,
            font=ctk.CTkFont(size=11),
            text_color=tag_color,
            anchor="w",
        )
        tag_label.grid(row=1, column=1, sticky="w", pady=(0, 8))

        # Botões
        btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=(4, 8), pady=6)

        apply_btn = ctk.CTkButton(
            btn_frame, text="Aplicar", width=80, height=28,
            fg_color="#4299e1", hover_color="#3182ce",
            command=lambda w=wp: self._apply_wallpaper(w),
            state="normal" if self.has_mpvpaper else "disabled",
        )
        apply_btn.pack(side="left", padx=(0, 6))

        opt_btn = ctk.CTkButton(
            btn_frame, text="Otimizar", width=80, height=28,
            fg_color="#805ad5", hover_color="#6b46c1",
            command=lambda w=wp: self._optimize_wallpaper(w),
            state="normal" if self.has_ffmpeg else "disabled",
        )
        opt_btn.pack(side="left")

    def _load_thumbnail(self, wp):
        """Carrega ou gera thumbnail para um wallpaper."""
        thumb_path = ThumbnailCache.get_or_create(wp)

        if thumb_path and os.path.exists(thumb_path):
            try:
                img = Image.open(thumb_path)
                if hasattr(img, "format") and img.format == "GIF":
                    img.seek(0)
                    img = img.convert("RGB")
                img.thumbnail(self.THUMB_SIZE, Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=self.THUMB_SIZE)
                self.thumb_refs.append(ctk_img)
                return ctk_img
            except Exception as e:
                logging.warning("Erro ao carregar thumbnail: %s", e)

        # Placeholder
        placeholder = Image.new("RGB", self.THUMB_SIZE, color=(45, 45, 50))
        ctk_img = ctk.CTkImage(light_image=placeholder, dark_image=placeholder, size=self.THUMB_SIZE)
        self.thumb_refs.append(ctk_img)
        return ctk_img

    # ── Aplicar wallpaper ────────────────────────────────────────────────

    def _apply_wallpaper(self, wp):
        fps = self._get_current_fps()
        success = WallpaperManager.apply(wp.file_path, fps)
        if success:
            self.config.set("last_wallpaper", wp.file_path)
            self._set_status(f"✅ Aplicado: {wp.title} ({fps} fps)")
        else:
            if not self.has_mpvpaper:
                messagebox.showerror(
                    "mpvpaper não encontrado",
                    "O mpvpaper não está instalado.\n\n"
                    "Instale com:\n  sudo apt install mpvpaper",
                )
            else:
                messagebox.showerror("Erro", "Falha ao aplicar wallpaper. Verifique o log.")

    # ── Otimizar vídeo ───────────────────────────────────────────────────

    def _optimize_wallpaper(self, wp):
        if not self.has_ffmpeg:
            messagebox.showwarning(
                "ffmpeg não encontrado",
                "O ffmpeg não está instalado.\n\n"
                "Instale com:\n  sudo apt install ffmpeg",
            )
            return

        # Diálogo para salvar
        base_name = os.path.splitext(os.path.basename(wp.file_path))[0]
        output_path = filedialog.asksaveasfilename(
            title="Salvar vídeo otimizado",
            defaultextension=".mp4",
            initialfile=f"{base_name}_otimizado.mp4",
            filetypes=[("MP4", "*.mp4")],
        )
        if not output_path:
            return

        # Mostrar barra de progresso
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Otimizando: {wp.title}...")

        def on_progress(pct):
            self.after(0, lambda: self.progress_bar.set(pct))
            self.after(0, lambda: self.progress_label.configure(
                text=f"Otimizando: {int(pct * 100)}%"
            ))

        def on_done(success):
            def _finish():
                self.progress_frame.grid_remove()
                if success:
                    self._set_status(f"✅ Otimizado: {os.path.basename(output_path)}")
                    messagebox.showinfo("Concluído", f"Vídeo otimizado salvo em:\n{output_path}")
                    self._refresh_list()
                else:
                    self._set_status("❌ Falha na otimização")
                    messagebox.showerror("Erro", "Falha ao otimizar vídeo. Verifique o log.")
            self.after(0, _finish)

        VideoOptimizer.optimize(wp.file_path, output_path, on_progress, on_done)

    # ── Fechar ───────────────────────────────────────────────────────────

    def _on_close(self):
        """Fecha a UI sem matar o mpvpaper (wallpaper continua rodando)."""
        self.destroy()

# ─── Modo Autostart ──────────────────────────────────────────────────────────

def run_autostart(config):
    """Aplica o último wallpaper salvo e sai (sem UI)."""
    last_wp = config.get("last_wallpaper", "")
    fps = config.get("fps", 30)

    if not last_wp or not os.path.exists(last_wp):
        logging.info("Autostart: nenhum wallpaper salvo ou arquivo não encontrado.")
        return

    logging.info("Autostart: aplicando %s (%d fps)", last_wp, fps)
    WallpaperManager.apply(last_wp, fps)

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    setup_logging()
    logging.info("Walpop v%s iniciado.", APP_VERSION)

    config = ConfigManager()

    # Modo autostart: aplicar e sair
    if "--autostart" in sys.argv:
        run_autostart(config)
        return

    # Modo normal: abrir UI
    app = WalpopApp(config)
    app.mainloop()

if __name__ == "__main__":
    main()
