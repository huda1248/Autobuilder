#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p config
test -f config/autobuild.yml || cat > config/autobuild.yml <<'YAML'
project_name: "Autobuilder"
projects:
  - { name: "Autobuilder", path: "." }
YAML

rm -rf build/gui_qt build/spec/Autobuild_Qt "dist/Autobuild Desktop.app"

pyinstaller \
  --name "Autobuild Desktop" \
  --windowed \
  --noconfirm --clean \
  --distpath dist \
  --workpath build/gui_qt \
  --specpath build/spec/Autobuild_Qt \
  --hidden-import PySide6 \
  --hidden-import PySide6.QtWebEngineWidgets \
  --collect-submodules PySide6 \
  --collect-data PySide6 \
  tools/autobuild_desktop_qt.py

echo
echo "✅ Built: dist/Autobuild Desktop.app"
echo 'Run: open "dist/Autobuild Desktop.app"'
