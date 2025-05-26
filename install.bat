@echo off
setlocal enabledelayedexpansion

echo 🚀 Bienvenido al instalador ULTRA PRO de OTW MUSIC SYSTEM...
echo.

:: Verificar si Python está instalado
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Python no encontrado. Descargando Python 3.11.9...
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe -OutFile python_installer.exe"
    
    echo 🛠️ Instalando Python...
    start /wait "" "%cd%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1

    echo ✅ Python instalado. Borrando instalador...
    del /f /q python_installer.exe

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

:: Instalar selenium y webdriver_manager
python -m pip install selenium webdriver-manager

:: Instalar numpy con una rueda precompilada si no funciona
python -m pip install numpy==1.24.3

:: Si numpy falla, descargar una rueda precompilada desde Gohlke y luego instalarla
if %errorlevel% neq 0 (
    echo ⚠️ Error con numpy. Intentando instalar la rueda precompilada...
    powershell -Command "Invoke-WebRequest -Uri https://download.lfd.uci.edu/pythonlibs/wk7fhnxw/numpy-1.24.3-cp312-cp312-win_amd64.whl -OutFile numpy-1.24.3-cp312-cp312-win_amd64.whl"
    python -m pip install numpy-1.24.3-cp312-cp312-win_amd64.whl
)

:: Instalar otros paquetes desde requirements.txt
python -m pip install -r requirements.txt

:: Lanzar el bot
echo 🚀 Lanzando el bot...
cd /d "%~dp0"
python main.py

pause
