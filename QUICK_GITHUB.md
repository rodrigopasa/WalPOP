# ⚡ Comandos Rápidos para GitHub

## Opción 1: Copiar y Pegar Todo (Más Rápido)

```bash
cd /home/angel/Documents/PopWallpaper

# Inicializar git
git init

# Agregar todos los archivos
git add .

# Primer commit
git commit -m "Initial commit: PopWallpaper

Modern Wallpaper Engine manager for Pop!_OS 24.04
- GUI with customtkinter
- Steam Workshop scanner
- Multi-format preview support (JPG, PNG, GIF)
- mpvpaper integration
- Desktop shortcut installer

"

# Ver lo que se va a subir
git log --oneline
```

**Ahora crea el repositorio en GitHub:**
1. Ve a: https://github.com/new
2. Nombre: `PopWallpaper`
3. Descripción: `🎨 Modern GUI for Wallpaper Engine on Pop!_OS (Wayland/COSMIC)`
4. **NO marques** "Initialize with README"
5. Clic en "Create repository"

**Después de crear el repo en GitHub, ejecuta:**

```bash
# Reemplaza TU_USUARIO con tu usuario de GitHub
git remote add origin https://github.com/TU_USUARIO/PopWallpaper.git
git branch -M main
git push -u origin main
```

---

## Opción 2: Paso por Paso

### 1. Inicializar Git
```bash
cd /home/angel/Documents/PopWallpaper
git init
```

### 2. Configurar usuario (si es primera vez)
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

### 3. Agregar archivos
```bash
git add .
git status  # Ver qué se agregó
```

### 4. Commit
```bash
git commit -m "Initial commit: PopWallpaper"
```

### 5. Crear repo en GitHub (manual)
- https://github.com/new
- Nombre: `PopWallpaper`
- Sin README inicial

### 6. Conectar y subir
```bash
git remote add origin https://github.com/TU_USUARIO/PopWallpaper.git
git branch -M main
git push -u origin main
```

---

## ✅ Verificar que todo está bien

```bash
# Ver el commit
git log

# Ver archivos ignorados
git status --ignored

# Ver archivos que se subirán
git ls-files
```

---

## 🔄 Actualizaciones futuras

```bash
# Cuando hagas cambios
git add .
git commit -m "Descripción del cambio"
git push
```

---

## 🏷️ Topics recomendados para GitHub

Agregar en la página del repositorio:
- `wallpaper-engine`
- `pop-os`
- `linux`
- `python`
- `customtkinter`
- `mpvpaper`
- `wayland`


---

## ⚠️ Importante

- Reemplaza `TU_USUARIO` con tu usuario real de GitHub
- Reemplaza `YOUR_USERNAME` en el README.md antes del push:
  ```bash
  # En README.md, cambia:
  git clone https://github.com/YOUR_USERNAME/PopWallpaper.git
  # Por:
  git clone https://github.com/TU_USUARIO_REAL/PopWallpaper.git
  ```

---

## 📝 Archivos preparados para GitHub

✅ **README.md** - Con badges, documentación completa  
✅ **LICENSE** - MIT  
✅ **.gitignore** - Excluye venv, cache, etc.  
✅ **GITHUB_SETUP.md** - Guía detallada (este archivo resumido)  

---

**¡Todo listo para subir a GitHub! 🚀**
