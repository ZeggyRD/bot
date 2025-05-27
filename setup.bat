@echo off
echo Setting up OTWMusicSystem...

REM Check for Python 3.10+ (basic check, might need a more robust one)
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH. Please install Python 3.10+ and try again.
    goto :eof
)

for /f "tokens=2 delims=. " %%v in ('python -c "import sys; print(sys.version_info.major)"') do set MAJOR_VERSION=%%v
for /f "tokens=2 delims=. " %%v in ('python -c "import sys; print(sys.version_info.minor)"') do set MINOR_VERSION=%%v

if %MAJOR_VERSION% LSS 3 (
    echo Error: Python 3.10 or higher is required. Found version %MAJOR_VERSION%.%MINOR_VERSION%.
    goto :eof
)
if %MAJOR_VERSION% EQU 3 if %MINOR_VERSION% LSS 10 (
    echo Error: Python 3.10 or higher is required. Found version %MAJOR_VERSION%.%MINOR_VERSION%.
    goto :eof
)


REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment 'venv'...
    python -m venv venv
) else (
    echo Virtual environment 'venv' already exists.
)

REM Activate virtual environment
echo Activating virtual environment...
call "venv\Scripts\activate.bat"

REM Upgrade pip and install requirements
echo Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies.
    goto :eof
)

echo Setup complete. Virtual environment 'venv' is ready and dependencies are installed.
echo To activate the environment, run: venv\Scripts\activate.bat

REM Placeholder for smoke tests - to be added in a later phase
echo Skipping smoke tests for now.
