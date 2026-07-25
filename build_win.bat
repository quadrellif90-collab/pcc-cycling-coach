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

REM 4. Build with PyInstaller (ppc.spec produces dist\VELARCO\VELARCO.exe)
echo Building...
pyinstaller ppc.spec --clean --noconfirm

echo.
echo === Build complete ===
echo Executable: dist\VELARCO\VELARCO.exe
echo.
echo To create the installer, compile installer.nsi with NSIS:
echo   makensis installer.nsi   ->   VELARCO-Setup-<ver>.exe
echo To run: dist\VELARCO\VELARCO.exe
REM (no `pause` — would hang CI runners waiting for input)
