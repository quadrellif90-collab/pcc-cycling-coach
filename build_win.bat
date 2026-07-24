@echo off
REM Build PPC — Programming Cycling Coach for Windows
REM Output: dist\PPC\PPC.exe  (then installer.nsi -> PPC-Setup-<ver>.exe)

cd /d "%~dp0"

echo === PPC Windows Build ===

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

REM 4. Build with PyInstaller (ppc.spec produces dist\PPC\PPC.exe)
echo Building...
pyinstaller ppc.spec --clean --noconfirm

echo.
echo === Build complete ===
echo Executable: dist\PPC\PPC.exe
echo.
echo To create the installer, compile installer.nsi with Inno Setup:
echo   iscc installer.nsi   ->   PPC-Setup-<ver>.exe  (silenzioso: PPC-Setup.exe /S)
echo To run: dist\PPC\PPC.exe
REM (no `pause` — would hang CI runners waiting for input)
