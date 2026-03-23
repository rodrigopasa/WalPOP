#!/usr/bin/env python3
"""
Walpop v2.0 — Gerenciador de Wallpapers Animados para Pop!_OS 24.04
Usa mpvpaper (Wayland) para aplicar wallpapers de vídeo.
Interface em português brasileiro com customtkinter (tema dark).
"""

import os
import sys
import json
import time
import shutil
import hashlib
import logging
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import random

import psutil
import pystray
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
SPEED_VALUES = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
SHUFFLE_VALUES = {"Desativado": 0, "5 Min": 5, "15 Min": 15, "1 Hora": 60, "1 Dia": 1440}

DEFAULT_CONFIG = {
    "fps": 30,
    "speed": 1.0,
    "custom_folder": "",
    "last_wallpaper": "",
    "autostart": False,
    "favorites": [],
    "monitor": "*",
    "shuffle_interval": 0,
    "smart_pause_battery": False,
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


def get_executable_path():
    """Retorna o caminho do executável (se compilado) ou do script atual."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)


def get_script_dir():
    """Retorna o diretório do script ou do executável."""
    return os.path.dirname(get_executable_path())


def get_venv_python():
    """Retorna o caminho do python do venv se existir, senão python3 do sistema."""
    venv_py = os.path.join(get_script_dir(), "venv", "bin", "python3")
    if os.path.exists(venv_py):
        return venv_py
    return "python3"

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

# ─── Managers de Background (Automação) ──────────────────────────────────────

class SmartPauseManager:
    """Pausa mpvpaper automaticamente quando na bateria."""
    _thread = None
    _stop_event = threading.Event()
    _is_paused = False
    
    @classmethod
    def set_paused(cls, pause):
        if pause == cls._is_paused:
            return
        cls._is_paused = pause
        try:
            cmd = ["pkill", "-STOP" if pause else "-CONT", "-f", "mpvpaper"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info("🔋 SmartPause: %s mpvpaper (%s)", "Pausado" if pause else "Retomado", "Bateria" if pause else "Tomada")
        except Exception as e:
            logging.warning("Erro enviar sinal de pausa: %s", e)

    @classmethod
    def start(cls, config: ConfigManager):
        if not config.get("smart_pause_battery", False):
            cls.stop()
            if cls._is_paused:
                cls.set_paused(False)
            return
            
        cls._stop_event.clear()
        if cls._thread and cls._thread.is_alive():
            return
            
        def _run():
            while not cls._stop_event.is_set():
                if hasattr(psutil, "sensors_battery"):
                    batt = psutil.sensors_battery()
                    if batt:
                        cls.set_paused(not batt.power_plugged)
                time.sleep(15)
                
        cls._thread = threading.Thread(target=_run, daemon=True)
        cls._thread.start()
        
    @classmethod
    def stop(cls):
        cls._stop_event.set()


class ShuffleManager:
    """Muda os wallpapers baseado no intervalo estipulado e favoritos."""
    _thread = None
    _stop_event = threading.Event()
    
    @classmethod
    def start(cls, config: ConfigManager, app_ref):
        interval_min = config.get("shuffle_interval", 0)
        if interval_min <= 0:
            cls.stop()
            return
            
        cls._stop_event.clear()
        if cls._thread and cls._thread.is_alive():
            return
            
        def _run():
            while not cls._stop_event.is_set():
                for _ in range(int(interval_min * 60)):
                    if cls._stop_event.is_set():
                        return
                    time.sleep(1)
                
                # Executa o shuffle
                if app_ref.wallpapers:
                    fav_paths = config.get("favorites", [])
                    favs = [wp for wp in app_ref.wallpapers if wp.file_path in fav_paths]
                    pool = favs if favs else app_ref.wallpapers
                    if pool:
                        wp = random.choice(pool)
                        app_ref.after(0, lambda w=wp: app_ref._apply_wallpaper(w, is_shuffle=True))
                        
        cls._thread = threading.Thread(target=_run, daemon=True)
        cls._thread.start()
        
    @classmethod
    def stop(cls):
        cls._stop_event.set()


class SystemTray:
    """Ícone na bandeja do sistema."""
    _icon = None
    
    @classmethod
    def run(cls, app_ref):
        if cls._icon:
            return
        
        img = Image.new('RGB', (64, 64), color=(66, 153, 225))
        try:
            icon_path = os.path.join(get_script_dir(), "assets", "icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
        except Exception:
            pass

        def _on_show():
            app_ref.after(0, app_ref.deiconify)
            
        def _on_next():
            if app_ref.wallpapers:
                fav_paths = app_ref.config.get("favorites", [])
                pool = [wp for wp in app_ref.wallpapers if wp.file_path in fav_paths] or app_ref.wallpapers
                if pool:
                    wp = random.choice(pool)
                    app_ref.after(0, lambda w=wp: app_ref._apply_wallpaper(w, is_shuffle=True))

        def _on_stop():
            app_ref.after(0, app_ref._on_close_full)

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Interface...", _on_show, default=True),
            pystray.MenuItem("Próximo Aleatório", _on_next),
            pystray.MenuItem("Sair Totalmente", _on_stop)
        )
        
        cls._icon = pystray.Icon("Walpop", img, "Walpop", menu)
        threading.Thread(target=cls._icon.run, daemon=True).start()
        
    @classmethod
    def stop(cls):
        if cls._icon:
            cls._icon.stop()

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

        try:
            entries = os.listdir(workshop_path)
        except PermissionError as e:
            logging.error("Sem permissão para ler Steam Workshop: %s", e)
            return wallpapers

        for folder_name in entries:
            folder_path = os.path.join(workshop_path, folder_name)
            if not os.path.isdir(folder_path):
                continue

            project_json = os.path.join(folder_path, "project.json")
            if not os.path.exists(project_json):
                continue

            try:
                with open(project_json, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Ignorar scene e web — apenas video
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
        """Escaneia todos os vídeos de uma pasta customizada (recursivo 1 nível)."""
        wallpapers = []

        if not folder_path or not os.path.isdir(folder_path):
            return wallpapers

        logging.info("Escaneando pasta customizada: %s", folder_path)

        try:
            entries = os.listdir(folder_path)
        except PermissionError as e:
            logging.error("Sem permissão para ler pasta custom: %s", e)
            return wallpapers

        for entry in entries:
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

        # Gerar thumbnail — -ss antes de -i é mais rápido (seek no input)
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-ss", "00:00:01",
                    "-i", wallpaper.file_path,
                    "-vframes", "1",
                    "-vf", "scale=160:90",
                    "-q:v", "8",
                    "-y", thumb_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=15,
            )
            if result.returncode == 0 and os.path.exists(thumb_path):
                logging.info("Thumbnail gerado: %s", thumb_path)
                return thumb_path
            else:
                stderr_msg = result.stderr.decode(errors="replace")[-200:] if result.stderr else ""
                logging.warning("ffmpeg falhou para thumbnail: %s", stderr_msg)
        except subprocess.TimeoutExpired:
            logging.warning("Timeout gerando thumbnail para %s", wallpaper.file_path)
        except Exception as e:
            logging.warning("Falha ao gerar thumbnail para %s: %s", wallpaper.file_path, e)

        return None

    @classmethod
    def generate_missing_async(cls, wallpapers, on_complete=None):
        """Gera thumbnails faltantes em background thread."""

        def _worker():
            count = 0
            for wp in wallpapers:
                if wp.preview_path and os.path.exists(wp.preview_path):
                    continue
                thumb_path = cls.get_thumb_path(wp.file_path)
                if os.path.exists(thumb_path):
                    continue
                cls.get_or_create(wp)
                count += 1
            logging.info("Thumbnails gerados em background: %d", count)
            if on_complete:
                on_complete(count)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return thread

# ─── WallpaperManager ────────────────────────────────────────────────────────

class WallpaperManager:
    """Aplica wallpapers usando mpvpaper."""

    HAS_MPVPAPER = check_command("mpvpaper")

    @classmethod
    def kill_existing(cls):
        """Mata todas as instâncias do mpvpaper."""
        try:
            subprocess.run(
                ["pkill", "-f", "mpvpaper"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.4)
        except Exception as e:
            logging.warning("Erro ao matar mpvpaper: %s", e)

    @classmethod
    def apply(cls, video_path, fps=30, speed=1.0, monitor="*"):
        """Mata mpvpaper anterior e aplica novo wallpaper."""
        if not cls.HAS_MPVPAPER:
            logging.error("mpvpaper não está instalado.")
            return False

        if not os.path.exists(video_path):
            logging.error("Arquivo de vídeo não encontrado: %s", video_path)
            return False

        try:
            cls.kill_existing()

            # mpvpaper: usando monitor da config
            escaped_path = video_path.replace("'", "'\\''")
            monitor_arg = f"'{monitor}'" if monitor else "'*'"
            shell_cmd = f"mpvpaper -o 'loop --vf=fps={fps} --speed={speed}' {monitor_arg} '{escaped_path}'"

            subprocess.Popen(
                shell_cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logging.info("Wallpaper aplicado: %s (Mon: %s, FPS: %d, Speed: %sx)", video_path, monitor, fps, speed)
            return True

        except Exception as e:
            logging.error("Erro ao aplicar wallpaper: %s", e)
            return False

    @classmethod
    def is_running(cls):
        """Verifica se um processo mpvpaper está ativo."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "mpvpaper"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except Exception:
            return False

# ─── VideoOptimizer ──────────────────────────────────────────────────────────

class VideoOptimizer:
    """Otimiza vídeos usando ffmpeg em thread separada."""

    HAS_FFMPEG = check_command("ffmpeg")

    @staticmethod
    def _get_duration(input_path):
        """Retorna a duração do vídeo em segundos, ou 0 se falhar."""
        try:
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    input_path,
                ],
                capture_output=True, text=True, timeout=10,
            )
            if probe.returncode == 0 and probe.stdout.strip():
                return float(probe.stdout.strip())
        except Exception as e:
            logging.warning("ffprobe falhou para %s: %s", input_path, e)
        return 0

    @classmethod
    def optimize(cls, input_path, output_path, progress_callback=None, done_callback=None):
        """Roda otimização em thread separada."""

        def _run():
            try:
                total_duration = cls._get_duration(input_path)

                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", "scale=1280:720:force_original_aspect_ratio=decrease",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "28",
                    "-an",
                    "-movflags", "+faststart",
                    "-progress", "pipe:1",
                    "-nostats",
                    "-y", output_path,
                ]

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                for line in process.stdout:
                    line = line.strip()
                    # Tentar out_time_us (mais novo) e out_time_ms (fallback)
                    if line.startswith("out_time_us="):
                        try:
                            time_us = int(line.split("=")[1])
                            time_s = time_us / 1_000_000
                            if total_duration > 0 and progress_callback:
                                pct = min(time_s / total_duration, 1.0)
                                progress_callback(pct)
                        except (ValueError, IndexError):
                            pass
                    elif line.startswith("out_time_ms="):
                        try:
                            time_ms = int(line.split("=")[1])
                            time_s = time_ms / 1_000_000
                            if total_duration > 0 and progress_callback:
                                pct = min(time_s / total_duration, 1.0)
                                progress_callback(pct)
                        except (ValueError, IndexError):
                            pass

                process.wait()

                if process.returncode == 0:
                    # Verificar se o output foi realmente criado
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logging.info("Vídeo otimizado: %s", output_path)
                        if done_callback:
                            done_callback(True)
                    else:
                        logging.error("ffmpeg finalizou mas output vazio/inexistente")
                        if done_callback:
                            done_callback(False)
                else:
                    stderr_out = process.stderr.read() if process.stderr else ""
                    logging.error("ffmpeg retornou código %d: %s", process.returncode, stderr_out[-500:])
                    # Limpar arquivo parcial
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except OSError:
                            pass
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
        """Cria arquivo de autostart apontando para o binário ou script python."""
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        
        exec_path = get_executable_path()
        if getattr(sys, 'frozen', False):
            exec_line = f"Exec={exec_path} --autostart"
        else:
            python_path = get_venv_python()
            exec_line = f"Exec={python_path} {exec_path} --autostart"

        content = f"""[Desktop Entry]
Type=Application
Name=Walpop
{exec_line}
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

    @staticmethod
    def is_enabled():
        """Verifica se o autostart está realmente ativo."""
        return os.path.exists(AUTOSTART_FILE)

# ─── UI Principal ─────────────────────────────────────────────────────────────

class WalpopApp(ctk.CTk):
    """Interface gráfica principal do Walpop."""

    THUMB_SIZE = (80, 45)  # 16:9

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.wallpapers = []
        self.thumb_refs = []  # Manter referências para GC
        self._is_scanning = False
        self._is_optimizing = False

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

        # Trays e Backgrounds
        SystemTray.run(self)
        SmartPauseManager.start(self.config)
        ShuffleManager.start(self.config, self)

        # Carregar wallpapers na inicialização
        self.after(300, self._refresh_list)

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # row 3 = lista scrollable

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
        warning_row = 1
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

        # ── Barra de busca e favoritos ────────────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))
        search_frame.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="🔍 Buscar wallpaper...")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_and_render_list())

        # ── Lista de wallpapers (scrollable) ────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Wallpapers")
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(6, 6))
        self.list_frame.grid_columnconfigure(1, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="Nenhum wallpaper encontrado",
            text_color="gray",
            font=ctk.CTkFont(size=14),
        )

        # ── Barra de progresso (otimização) ──────────────────────────────
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 2))
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
        controls.grid(row=5, column=0, sticky="ew", padx=16, pady=(4, 12))
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

        saved_fps = self.config.get("fps", 30)
        idx = FPS_VALUES.index(saved_fps) if saved_fps in FPS_VALUES else 3
        self.fps_slider.set(idx)

        self.fps_label = ctk.CTkLabel(
            fps_frame, text=f"{saved_fps} fps",
            font=ctk.CTkFont(size=13, weight="bold"), width=60,
        )
        self.fps_label.grid(row=0, column=2, padx=(8, 0))

        # Speed slider
        speed_frame = ctk.CTkFrame(controls, fg_color="transparent")
        speed_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        speed_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(speed_frame, text="Velocidade:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        self.speed_slider = ctk.CTkSlider(
            speed_frame, from_=0, to=len(SPEED_VALUES)-1, number_of_steps=len(SPEED_VALUES)-1,
            command=self._on_speed_change,
        )
        self.speed_slider.grid(row=0, column=1, sticky="ew")

        saved_speed = self.config.get("speed", 1.0)
        idx_speed = SPEED_VALUES.index(saved_speed) if saved_speed in SPEED_VALUES else 3
        self.speed_slider.set(idx_speed)

        self.speed_label = ctk.CTkLabel(
            speed_frame, text=f"{saved_speed}x",
            font=ctk.CTkFont(size=13, weight="bold"), width=60,
        )
        self.speed_label.grid(row=0, column=2, padx=(8, 0))

        # Monitor Input
        mon_frame = ctk.CTkFrame(controls, fg_color="transparent")
        mon_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        mon_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(mon_frame, text="Monitor:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.monitor_entry = ctk.CTkEntry(mon_frame, placeholder_text="* (Todos) ou eDP-1")
        self.monitor_entry.grid(row=0, column=1, sticky="ew")
        self.monitor_entry.insert(0, self.config.get("monitor", "*"))
        self.monitor_entry.bind("<KeyRelease>", lambda e: self.config.set("monitor", self.monitor_entry.get().strip() or "*"))

        # Shuffle Control
        shuf_frame = ctk.CTkFrame(controls, fg_color="transparent")
        shuf_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        shuf_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(shuf_frame, text="Trocar Auto:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.shuffle_combo = ctk.CTkComboBox(shuf_frame, values=list(SHUFFLE_VALUES.keys()), command=self._on_shuffle_change)
        self.shuffle_combo.grid(row=0, column=1, sticky="ew")
        saved_shuf = self.config.get("shuffle_interval", 0)
        shuf_key = "Desativado"
        for k, v in SHUFFLE_VALUES.items():
            if v == saved_shuf:
                shuf_key = k
                break
        self.shuffle_combo.set(shuf_key)

        # Switches (Row 4)
        sw_frame = ctk.CTkFrame(controls, fg_color="transparent")
        sw_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        # Autostart toggle
        actual_autostart = AutostartManager.is_enabled()
        if actual_autostart != self.config.get("autostart", False):
            self.config.set("autostart", actual_autostart)

        self.autostart_var = ctk.BooleanVar(value=actual_autostart)
        self.autostart_switch = ctk.CTkSwitch(
            sw_frame, text="Boot", variable=self.autostart_var,
            command=self._on_autostart_toggle, font=ctk.CTkFont(size=13)
        )
        self.autostart_switch.pack(side="left")

        # Smart Pause
        self.smart_pause_var = ctk.BooleanVar(value=self.config.get("smart_pause_battery", False))
        self.smart_pause_switch = ctk.CTkSwitch(
            sw_frame, text="Pausar na Bateria", variable=self.smart_pause_var,
            command=self._on_smart_pause_toggle, font=ctk.CTkFont(size=13)
        )
        self.smart_pause_switch.pack(side="left", padx=(16, 0))

        # Botão atualizar
        self.refresh_btn = ctk.CTkButton(
            sw_frame, text="🔄 Atualizar lista", command=self._refresh_list, width=120
        )
        self.refresh_btn.pack(side="right")

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
        idx = max(0, min(idx, len(FPS_VALUES) - 1))
        return FPS_VALUES[idx]

    def _on_fps_change(self, value):
        fps = self._get_current_fps()
        self.fps_label.configure(text=f"{fps} fps")
        self.config.set("fps", fps)

    def _get_current_speed(self):
        idx = int(round(self.speed_slider.get()))
        idx = max(0, min(idx, len(SPEED_VALUES) - 1))
        return SPEED_VALUES[idx]

    def _on_speed_change(self, value):
        speed = self._get_current_speed()
        self.speed_label.configure(text=f"{speed}x")
        self.config.set("speed", speed)

    def _on_autostart_toggle(self):
        enabled = self.autostart_var.get()
        self.config.set("autostart", enabled)
        if enabled:
            AutostartManager.enable()
            self._set_status("✅ Autostart ativado")
        else:
            AutostartManager.disable()
            self._set_status("Autostart desativado")

    def _on_shuffle_change(self, value):
        val = SHUFFLE_VALUES.get(value, 0)
        self.config.set("shuffle_interval", val)
        ShuffleManager.start(self.config, self)

    def _on_smart_pause_toggle(self):
        enabled = self.smart_pause_var.get()
        self.config.set("smart_pause_battery", enabled)
        SmartPauseManager.start(self.config)

    def _toggle_favorite(self, wp):
        favs = self.config.get("favorites", [])
        if wp.file_path in favs:
            favs.remove(wp.file_path)
        else:
            favs.append(wp.file_path)
        self.config.set("favorites", favs)
        self._filter_and_render_list()

    def _set_status(self, text):
        self.status_label.configure(text=text)

    # ── Lista de wallpapers ──────────────────────────────────────────────

    def _refresh_list(self):
        """Escaneia wallpapers em background thread para não travar a UI."""
        if self._is_scanning:
            return

        self._is_scanning = True
        self.refresh_btn.configure(state="disabled")
        self._set_status("Escaneando wallpapers...")
        self.update()

        custom_folder = self.custom_entry.get().strip()
        if custom_folder:
            self.config.set("custom_folder", custom_folder)

        def _scan_worker():
            wallpapers = WallpaperScanner.scan_all(custom_folder)
            self.after(0, lambda: self._on_scan_complete(wallpapers))

        thread = threading.Thread(target=_scan_worker, daemon=True)
        thread.start()

    def _on_scan_complete(self, wallpapers):
        """Callback na main thread após scan terminar."""
        self._is_scanning = False
        self.refresh_btn.configure(state="normal")
        self.wallpapers = wallpapers
        self._filter_and_render_list()

        # Gerar thumbnails faltantes em background e recarregar depois
        missing = [wp for wp in self.wallpapers
                   if not wp.preview_path and not os.path.exists(ThumbnailCache.get_thumb_path(wp.file_path))]
        if missing and self.has_ffmpeg:
            def _on_thumbs_done(count):
                if count > 0:
                    self.after(0, self._reload_thumbnails)
            ThumbnailCache.generate_missing_async(missing, _on_thumbs_done)

    def _filter_and_render_list(self):
        query = self.search_entry.get().lower()
        favs = self.config.get("favorites", [])

        filtered = []
        for wp in self.wallpapers:
            if query in wp.title.lower() or query in wp.source.lower():
                filtered.append(wp)

        filtered.sort(key=lambda w: (0 if w.file_path in favs else 1, w.title.lower()))

        for child in self.list_frame.winfo_children():
            if child != self.empty_label:
                child.destroy()
        self.thumb_refs.clear()

        if not filtered:
            self.empty_label.grid(row=0, column=0, columnspan=4, pady=40)
            self._set_status("Nenhum wallpaper encontrado")
            return

        self.empty_label.grid_remove()

        for i, wp in enumerate(filtered):
            self._add_wallpaper_row(i, wp)

        self._set_status(f"{len(filtered)} wallpapers encontrados")

    def _reload_thumbnails(self):
        """Recarrega a lista após geração de thumbnails em background."""
        if not self._is_scanning:
            self._set_status("Atualizando thumbnails...")
            # Recarregar sem re-escanear
            self._filter_and_render_list()

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

        # Indicar wallpaper ativo
        is_active = self.config.get("last_wallpaper", "") == wp.file_path

        # Botões
        btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=(4, 8), pady=6)

        is_fav = wp.file_path in self.config.get("favorites", [])
        fav_text = "⭐" if is_fav else "☆"
        fav_btn = ctk.CTkButton(
            btn_frame, text=fav_text, width=32, height=28,
            fg_color="transparent", hover_color="#2d3748", text_color="#ecc94b",
            command=lambda w=wp: self._toggle_favorite(w),
        )
        fav_btn.pack(side="left", padx=(0, 6))

        apply_text = "✓ Ativo" if is_active else "Aplicar"
        apply_color = "#38a169" if is_active else "#4299e1"
        apply_hover = "#2f855a" if is_active else "#3182ce"

        apply_btn = ctk.CTkButton(
            btn_frame, text=apply_text, width=80, height=28,
            fg_color=apply_color, hover_color=apply_hover,
            command=lambda w=wp: self._apply_wallpaper(w),
            state="normal" if self.has_mpvpaper else "disabled",
        )
        apply_btn.pack(side="left", padx=(0, 6))

        opt_btn = ctk.CTkButton(
            btn_frame, text="Otimizar", width=80, height=28,
            fg_color="#805ad5", hover_color="#6b46c1",
            command=lambda w=wp: self._optimize_wallpaper(w),
            state="normal" if (self.has_ffmpeg and not self._is_optimizing) else "disabled",
        )
        opt_btn.pack(side="left")

    def _load_thumbnail(self, wp):
        """Carrega thumbnail para um wallpaper (do cache se existir)."""
        thumb_path = None

        # Prioridade: preview do Steam > cache gerado
        if wp.preview_path and os.path.exists(wp.preview_path):
            thumb_path = wp.preview_path
        else:
            cached = ThumbnailCache.get_thumb_path(wp.file_path)
            if os.path.exists(cached):
                thumb_path = cached

        if thumb_path:
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

        # Placeholder cinza
        placeholder = Image.new("RGB", self.THUMB_SIZE, color=(45, 45, 50))
        ctk_img = ctk.CTkImage(light_image=placeholder, dark_image=placeholder, size=self.THUMB_SIZE)
        self.thumb_refs.append(ctk_img)
        return ctk_img

    # ── Aplicar wallpaper ────────────────────────────────────────────────

    def _apply_wallpaper(self, wp, is_shuffle=False):
        fps = self._get_current_fps()
        speed = self._get_current_speed()
        mon = self.config.get("monitor", "*")
        
        mode_text = "[Shuffle] " if is_shuffle else ""
        self._set_status(f"Aplicando: {mode_text}{wp.title}...")
        self.update()

        success = WallpaperManager.apply(wp.file_path, fps, speed, monitor=mon)
        if success:
            self.config.set("last_wallpaper", wp.file_path)
            self._set_status(f"✅ Aplicado: {wp.title} ({fps} fps, {speed}x)")
            # Recarregar lista para atualizar indicador de ativo
            self._reload_thumbnails()
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

        if self._is_optimizing:
            messagebox.showinfo("Aguarde", "Já existe uma otimização em andamento.")
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

        # Bloquear nova otimização
        self._is_optimizing = True

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
                self._is_optimizing = False
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
        """Oculta a UI sem matar o mpvpaper. Fica na bandeja."""
        self.withdraw()

    def _on_close_full(self):
        """Fecha totalmente o aplicativo."""
        WallpaperManager.kill_existing()
        SystemTray.stop()
        SmartPauseManager.stop()
        ShuffleManager.stop()
        self.destroy()
        sys.exit(0)

# ─── Modo Autostart ──────────────────────────────────────────────────────────

def run_autostart(config):
    """Aplica o último wallpaper salvo e sai (sem UI)."""
    last_wp = config.get("last_wallpaper", "")
    fps = config.get("fps", 30)
    speed = config.get("speed", 1.0)

    if not last_wp:
        logging.info("Autostart: nenhum wallpaper configurado.")
        return

    if not os.path.exists(last_wp):
        logging.warning("Autostart: arquivo não encontrado: %s", last_wp)
        return

    # Esperar um pouco o compositor Wayland estar pronto
    time.sleep(2)

    logging.info("Autostart: aplicando %s (%d fps, %sx)", last_wp, fps, speed)
    success = WallpaperManager.apply(last_wp, fps, speed)
    if success:
        logging.info("Autostart: wallpaper aplicado com sucesso.")
    else:
        logging.error("Autostart: falha ao aplicar wallpaper.")

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
