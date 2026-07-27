#!/bin/bash
# Build PPC — Programming Cycling Coach for macOS
# Output: dist/PPC.app and PPC.dmg
set -e

echo "=== Building PPC for macOS ==="

# 1. Install dependencies
pip3 install -r requirements.txt pyinstaller

# 2. Create assets dir if missing
mkdir -p assets

# 3. Build with PyInstaller (ppc.spec produces dist/PPC.app)
pyinstaller pcc.spec --clean --noconfirm

echo ""
echo "=== Build complete ==="
echo "App: dist/PPC.app"

# 4. Create DMG (if create-dmg is installed)
if command -v create-dmg &> /dev/null; then
    echo "Creating DMG..."
    create-dmg \
        --volname "PPC" \
        
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon "PPC.app" 150 190 \
        --app-drop-link 450 190 \
        "PPC.dmg" \
        "dist/PPC.app"
    echo "DMG: PPC.dmg"
else
    echo ""
    echo "To create a DMG installer, install create-dmg:"
    echo "  brew install create-dmg"
    echo "Then re-run this script."
fi
