@echo off
REM Build VELARCO — Adaptive Cycling Intelligence for Windows
REM Output: dist\VELARCO\VELARCO.exe  (then installer.nsi -> VELARCO-Setup-<ver>.exe)

cd /d "%~dp0"

echo === VELARCO Windows Build ===

REM 1. Create virtual environment if needed
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

REM 2. Install dependencies
echo Installing dependencies...
pip install -r requirements.txt pyinstaller

REM 3. Create assets dir if missing
if not exist assets mkdir assets

REM 4. Build with PyInstaller (velarco.spec produces dist\VELARCO\VELARCO.exe)
echo Building...
pyinstaller velarco.spec --clean --noconfirm
if errorlevel 1 (
    echo PYINSTALLER FAILED
    exit /b 1
)

echo.
echo === Build complete ===
echo Executable: dist\VELARCO\VELARCO.exe
echo To run: dist\VELARCO\VELARCO.exe
REM (no `pause` — would hang CI runners waiting for input)
exit /b 0
