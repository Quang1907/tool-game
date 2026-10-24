#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo "=== Building Binh 13 Analyzer Standalone macOS App ==="

pyinstaller --noconfirm --onedir --windowed \
    --name "Binh13Analyzer" \
    --add-data "config/default_rules.json:config" \
    --osx-bundle-identifier "com.antigravity.binh13analyzer" \
    app/main.py

echo "Build complete! App bundle located at dist/Binh13Analyzer.app"
