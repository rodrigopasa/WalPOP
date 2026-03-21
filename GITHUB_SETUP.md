# 🚀 Subir PopWallpaper a GitHub

## Paso 1: Inicializar Git (si aún no lo has hecho)

```bash
cd /home/angel/Documents/PopWallpaper
git init
```

## Paso 2: Configurar usuario de Git (si es primera vez)

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu_email@ejemplo.com"
```

## Paso 3: Agregar archivos al repositorio

```bash
# Agregar todos los archivos (respetando .gitignore)
git add .

# Ver qué archivos se van a subir
git status
```

## Paso 4: Hacer el primer commit

```bash
git commit -m "Initial commit: PopWallpaper - Wallpaper Engine manager for Pop!_OS

- Modern GUI with customtkinter
- Steam Workshop wallpaper scanner
- Preview image support (JPG, PNG, GIF)
- mpvpaper integration for persistent wallpapers
- Desktop shortcut installer
"
```

## Paso 5: Crear repositorio en GitHub

1. Ve a https://github.com/new
2. Nombre del repositorio: `PopWallpaper`
3. Descripción: `🎨 Modern GUI for managing Wallpaper Engine content on Pop!_OS (Wayland/COSMIC)`
4. **NO** inicialices con README (ya lo tenemos)
5. Haz clic en "Create repository"

## Paso 6: Conectar repositorio local con GitHub

```bash
# Reemplaza YOUR_USERNAME con tu usuario de GitHub
git remote add origin https://github.com/YOUR_USERNAME/PopWallpaper.git

# Verificar que se agregó correctamente
git remote -v
```

## Paso 7: Subir código a GitHub

```bash
# Primera vez (crea la rama main)
git branch -M main
git push -u origin main

# Futuros pushes
git push
```

## Paso 8: Configurar repositorio en GitHub (Opcional)

### Topics (Etiquetas)
Agrega estos topics en la página del repositorio de GitHub:
- `wallpaper-engine`
- `pop-os`
- `linux`
- `python`
- `customtkinter`
- `mpvpaper`
- `wayland`


### Configuración del README
GitHub automáticamente mostrará tu README.md mejorado con:
- Badges

- Instrucciones de instalación
- Screenshots (cuando los agregues)

---

## 📸 Agregar Screenshots (Recomendado)

1. Crea una carpeta `screenshots/` en el repositorio
2. Toma capturas de pantalla de la aplicación
3. Agrega las imágenes a la carpeta
4. Actualiza el README.md:

```markdown
## Screenshots

![Main Interface](screenshots/main-ui.png)
*Modern dark UI with wallpaper list and preview*

![Wallpaper Applied](screenshots/wallpaper-applied.png)
*Animated wallpaper in action*
```

---

## 🔄 Futuras actualizaciones

Cuando hagas cambios:

```bash
# Ver archivos modificados
git status

# Agregar cambios
git add .

# Commit con mensaje descriptivo
git commit -m "Descripción de los cambios"

# Subir a GitHub
git push
```

---

## ✅ Checklist de publicación

- [ ] Git inicializado
- [ ] Primer commit realizado
- [ ] Repositorio creado en GitHub
- [ ] Remote origin configurado
- [ ] Código subido (`git push`)
- [ ] Topics agregados en GitHub
- [ ] README se ve correctamente
- [ ] LICENSE visible en GitHub
- [ ] (Opcional) Screenshots agregados
- [ ] (Opcional) GitHub Release creado

---

## 🎉 ¡Listo!

Tu proyecto está en GitHub con:

- ✅ Licencia MIT
- ✅ README profesional
- ✅ Documentación completa
- ✅ .gitignore configurado

**URL de tu repo:** `https://github.com/YOUR_USERNAME/PopWallpaper`

---

**Nota:** Recuerda reemplazar `YOUR_USERNAME` con tu usuario real de GitHub en el README.md antes del último commit.
