@echo off
REM Build PCC — Adaptive Cycling Intelligence for Windows
REM Output: dist\PCC\PCC.exe  (then installer.nsi -> PCC-Setup-<ver>.exe)

cd /d "%~dp0"

echo === PCC Windows Build ===

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

REM 4. Build with PyInstaller (pcc.spec produces dist\PCC\PCC.exe)
echo Building...
pyinstaller pcc.spec --clean --noconfirm
if errorlevel 1 (
    echo PYINSTALLER FAILED
    exit /b 1
)

echo.
echo === Build complete ===
echo Executable: dist\PCC\PCC.exe
echo To run: dist\PCC\PCC.exe
REM (no `pause` — would hang CI runners waiting for input)
exit /b 0
