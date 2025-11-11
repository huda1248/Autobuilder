#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Full clean to avoid stale PySide6 framework symlinks
rm -rf dist build/gui_qt build/spec/Autobuild_Qt \
  "$HOME/Library/Application Support/pyinstaller"

mkdir -p config
test -f config/autobuild.yml || cat > config/autobuild.yml <<'YAML'
project_name: "Autobuilder"
projects:
  - { name: "Autobuilder", path: "." }
YAML

pyinstaller \
  --name "Autobuild Desktop" \
  --windowed \
  --noconfirm --clean \
  --distpath dist \
  --workpath build/gui_qt \
  --specpath build/spec/Autobuild_Qt \
  \
  --hidden-import PySide6 \
  --hidden-import PySide6.QtWebEngineWidgets \
  --collect-submodules PySide6 \
  --collect-submodules PySide6.QtWebEngineWidgets \
  --collect-submodules PySide6.QtGui \
  --collect-data PySide6 \
  --collect-data PySide6.QtWebEngineWidgets \
  --collect-binaries PySide6 \
  --collect-binaries PySide6.QtWebEngineCore \
  tools/autobuild_desktop_qt.py

echo
echo "✅ Built: dist/Autobuild Desktop.app"
echo 'Run with logs: "./dist/Autobuild Desktop.app/Contents/MacOS/Autobuild Desktop"'
