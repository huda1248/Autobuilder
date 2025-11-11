#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Absolute source path (avoids any cwd confusion)
SRC="$(pwd)/tools/autobuild_desktop_tk.py"
[ -f "$SRC" ] || { echo "Missing $SRC"; exit 1; }

# Ensure default config exists
mkdir -p config
[ -f config/autobuild.yml ] || cat > config/autobuild.yml <<'YAML'
project_name: "Autobuilder"
workspace_dir: "./"
logs_dir: "./logs"
build:
  output_dir: "./dist"
  include_timestamp: false
  optimize: 0
features:
  textual_tui: true
  tkinter_gui: true
YAML

# Clean only GUI work/spec and the previous app bundle (keep other dist outputs)
rm -rf build/gui build/spec/Autobuild_Desktop "dist/Autobuild Desktop.app"

# Force a fresh, un-cached build and point at absolute SRC
pyinstaller \
  --name "Autobuild Desktop" \
  --windowed \
  --clean --noconfirm \
  --distpath dist \
  --workpath build/gui \
  --specpath build/spec/Autobuild_Desktop \
  "$SRC"

echo
echo "✅ Built: dist/Autobuild Desktop.app"
echo "Launch: open \"dist/Autobuild Desktop.app\""
