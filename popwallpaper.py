#!/usr/bin/env python3
"""
PopWallpaper - Wallpaper Engine Manager for Pop!_OS
Integración con lanzador.sh para persistencia total
"""

import os
import json
import subprocess
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

def truncate_text(text, max_length=40):
    """Trunca texto y agrega ... si excede el largo máximo"""
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

class Wallpaper:
    """Represents a wallpaper from Steam Workshop"""
    def __init__(self, title, file_path, preview_path, folder_path):
        self.title = title
        self.file_path = file_path
        self.preview_path = preview_path
        self.folder_path = folder_path

class WallpaperScanner:
    """Scans Steam Workshop directory"""
    
    # Rutas posibles de Steam
    WORKSHOP_PATHS = [
        os.path.expanduser("~/.steam/debian-installation/steamapps/workshop/content/431960"),
        os.path.expanduser("~/.local/share/Steam/steamapps/workshop/content/431960"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/workshop/content/431960"),
    ]
    VALID_EXTENSIONS = {'.mp4', '.webm'}
    
    @classmethod
    def get_workshop_path(cls):
        for path in cls.WORKSHOP_PATHS:
            if os.path.exists(path):
                return path
        return cls.WORKSHOP_PATHS[0]
    
    @classmethod
    def scan_wallpapers(cls):
        wallpapers = []
        workshop_path = cls.get_workshop_path()
        
        if not os.path.exists(workshop_path):
            return wallpapers
        
        for folder_name in os.listdir(workshop_path):
            folder_path = os.path.join(workshop_path, folder_name)
            if not os.path.isdir(folder_path): continue
            
            project_json = os.path.join(folder_path, "project.json")
            if not os.path.exists(project_json): continue
            
            try:
                with open(project_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Filtrar escenas y webs, solo queremos videos
                if data.get('type', '').lower() in ['scene', 'web']: continue
                
                title = data.get('title', f'Untitled ({folder_name})')
                file_name = data.get('file', '')
                if not file_name: continue
                
                # Verificar extensión de video
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext not in cls.VALID_EXTENSIONS: continue
                
                file_path = os.path.join(folder_path, file_name)
                if not os.path.exists(file_path): continue
                
                # ✅ FIX: Buscar preview en múltiples formatos (jpg, png, gif, jpeg)
                preview_path = None
                for ext in ['preview.jpg', 'preview.png', 'preview.gif', 'preview.jpeg']:
                    potential_preview = os.path.join(folder_path, ext)
                    if os.path.exists(potential_preview):
                        preview_path = potential_preview
                        break
                
                wallpapers.append(Wallpaper(title, file_path, preview_path, folder_path))
                
            except (json.JSONDecodeError, IOError):
                continue
        
        wallpapers.sort(key=lambda w: w.title.lower())
        return wallpapers

class WallpaperManager:
    """Gestiona la aplicación de fondos usando el script externo"""
    
    @staticmethod
    def apply_wallpaper(video_path):
        """
        Delega la ejecución al script 'lanzador.sh' para que el fondo
        sea independiente de esta aplicación (persistencia total).
        """
        try:
            # Buscamos lanzador.sh en la misma carpeta que este archivo
            launcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lanzador.sh")
            
            if not os.path.exists(launcher_path):
                messagebox.showerror("Error", f"No se encontró el archivo:\n{launcher_path}\n\nAsegúrate de haberlo creado.")
                return False

            # Ejecutamos el script pasando la ruta del video
            subprocess.Popen([launcher_path, video_path])
            return True
        except Exception as e:
            print(f"Error crítico lanzando script: {e}")
            return False

class PopWallpaperApp(ctk.CTk):
    """Interfaz Gráfica Principal"""
    
    def __init__(self):
        super().__init__()
        self.title("PopWallpaper Manager")
        self.geometry("1000x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.wallpapers = []
        self.current_wallpaper = None
        self.create_ui()
        
        # Al cerrar la ventana, NO matamos el proceso (el lanzador se encarga)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.load_wallpapers()
    
    def create_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.sidebar, text="Wallpapers", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=20)
        self.wallpaper_list = ctk.CTkScrollableFrame(self.sidebar, width=260)
        self.wallpaper_list.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(self.sidebar, text="🔄 Refresh List", command=self.load_wallpapers).grid(row=2, column=0, padx=20, pady=20)
        
        # Main Area
        self.main_panel = ctk.CTkFrame(self, corner_radius=0)
        self.main_panel.grid(row=0, column=1, sticky="nsew")
        self.main_panel.grid_rowconfigure(1, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)
        
        # ✅ FIX: Title Label con wrapping para nombres largos
        self.title_label = ctk.CTkLabel(
            self.main_panel, 
            text="Select a wallpaper", 
            font=ctk.CTkFont(size=24, weight="bold"),
            wraplength=680,  # Máximo ancho antes de word wrap
            justify="center"
        )
        self.title_label.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="ew")
        
        self.preview_frame = ctk.CTkFrame(self.main_panel)
        self.preview_frame.grid(row=1, column=0, padx=40, pady=20, sticky="nsew")
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="No preview available")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        
        self.apply_btn = ctk.CTkButton(self.main_panel, text="Apply Wallpaper", font=ctk.CTkFont(size=18, weight="bold"), height=50, command=self.apply_current_wallpaper, state="disabled")
        self.apply_btn.grid(row=2, column=0, padx=40, pady=40)
        
        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_bar.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

    def load_wallpapers(self):
        self.status_bar.configure(text="Scanning...")
        self.update()
        for w in self.wallpaper_list.winfo_children(): w.destroy()
        
        self.wallpapers = WallpaperScanner.scan_wallpapers()
        if not self.wallpapers:
            self.status_bar.configure(text="No wallpapers found")
            return

        for wp in self.wallpapers:
            frame = ctk.CTkFrame(self.wallpaper_list, fg_color="transparent")
            frame.pack(fill="x", padx=5, pady=5)
            
            thumb = None
            if wp.preview_path and os.path.exists(wp.preview_path):
                try:
                    img = Image.open(wp.preview_path)
                    # ✅ FIX: Si es GIF, extraer primer frame para thumbnail
                    if img.format == 'GIF':
                        img.seek(0)
                        img = img.convert('RGB')
                    img.thumbnail((50, 50), Image.Resampling.LANCZOS)
                    thumb = ctk.CTkImage(light_image=img, dark_image=img, size=(50, 50))
                except: pass
            
            
            # ✅ FIX: Truncar texto largo en sidebar
            display_name = truncate_text(wp.title, max_length=35)
            
            btn = ctk.CTkButton(
                frame, 
                text=display_name, 
                image=thumb, 
                compound="left", 
                anchor="w", 
                height=60 if thumb else 30,
                command=lambda w=wp: self.select_wallpaper(w)
            )
            btn.pack(fill="x")
            
            # ⚠️ NOTA: tooltip_text NO existe en customtkinter
            # La app crasheaba con: btn.configure(tooltip_text=wp.title)
            # Por ahora, tooltip deshabilitado hasta encontrar solución alternativa
        
        self.status_bar.configure(text=f"Found {len(self.wallpapers)} wallpapers")

    def select_wallpaper(self, wp):
        """Selecciona un wallpaper y actualiza el preview (soporta JPG, PNG, GIF)"""
        self.current_wallpaper = wp
        self.title_label.configure(text=wp.title)
        self.apply_btn.configure(state="normal")
        
        if wp.preview_path and os.path.exists(wp.preview_path):
            try:
                # Abrir la imagen (puede ser JPG, PNG, GIF, etc.)
                img = Image.open(wp.preview_path)
                
                # ✅ FIX: Si es GIF, extraer solo el primer frame
                if img.format == 'GIF':
                    img.seek(0)  # Ir al primer frame
                    img = img.convert('RGB')  # Convertir a RGB para compatibilidad
                
                # Calcular escala manteniendo proporción
                orig_w, orig_h = img.size
                scale = min(700/orig_w, 350/orig_h)
                new_size = (int(orig_w*scale), int(orig_h*scale))
                
                # Redimensionar imagen
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Crear CTkImage y almacenar referencia
                self.preview_image = ctk.CTkImage(
                    light_image=img_resized, 
                    dark_image=img_resized, 
                    size=new_size
                )
                
                # Configurar imagen en el label
                self.preview_label.configure(image=self.preview_image, text="")
                
                # ✅ CRÍTICO: Forzar actualización del widget
                self.preview_label.update_idletasks()
                self.preview_label.update()
                
            except Exception as e:
                print(f"Error loading preview: {e}")
                self.preview_label.configure(image=None, text="Preview error")
                self.preview_label.update()
        else:
            # Sin preview disponible
            self.preview_image = None
            self.preview_label.configure(image=None, text="No preview")
            self.preview_label.update()
        
        # Actualizar barra de estado
        self.status_bar.configure(text=f"Selected: {wp.title}")

    def apply_current_wallpaper(self):
        if self.current_wallpaper:
            if WallpaperManager.apply_wallpaper(self.current_wallpaper.file_path):
                self.status_bar.configure(text=f"Applied: {self.current_wallpaper.title}")
                # Opcional: Mostrar mensaje de éxito
                # messagebox.showinfo("Success", "Wallpaper applied!")

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    app = PopWallpaperApp()
    app.mainloop()
