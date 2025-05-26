@echo off
setlocal enabledelayedexpansion

echo 🚀 Bienvenido al instalador ULTRA PRO de OTW MUSIC SYSTEM...
echo.

:: Definir la URL oficial de Python (instalador silencioso)
set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
set PYTHON_INSTALLER=python_installer.exe

:: Verificar si Python está instalado
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Python no encontrado. Descargando Python 3.11.9...
    powershell -Command "Invoke-WebRequest -Uri !PYTHON_URL! -OutFile !PYTHON_INSTALLER!"
    
    echo 🛠️ Instalando Python...
    start /wait "" "%cd%\!PYTHON_INSTALLER!" /quiet InstallAllUsers=1 PrependPath=1

    echo ✅ Python instalado. Borrando instalador...
    del /f /q "!PYTHON_INSTALLER!"

    echo 🔄 Refrescando variables de entorno...
    setx PATH "%PATH%;C:\Program Files\Python311\;C:\Program Files\Python311\Scripts\"
)

:: Confirmar versión de Python
python --version
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no se instaló correctamente. Instálalo manualmente y vuelve a correr esto.
    pause
    exit /b
)

:: Actualizar pip
echo 🔄 Actualizando pip...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

:: Instalar dependencias necesarias
echo 📦 Instalando paquetes necesarios...
python -m pip install PyQt5 uiautomator2

:: Lanzar el bot
echo 🚀 Lanzando el bot...
cd /d "%~dp0"
python main.py

pause
