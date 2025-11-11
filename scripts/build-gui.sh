#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
cd "$(dirname "$0")/.."

# Detect entry (supports either tools/… or repo root)
if [[ -f tools/autobuild_desktop_tk.py ]]; then
  ENTRY="tools/autobuild_desktop_tk.py"
elif [[ -f autobuild_desktop_tk.py ]]; then
  ENTRY="autobuild_desktop_tk.py"
else
  echo "❌ Could not find autobuild_desktop_tk.py (tools/ or root)."
  exit 1
fi

# Ensure default config exists (harmless if already there)
if [[ ! -f config/autobuild.yml ]]; then
  mkdir -p config
  cat > config/autobuild.yml <<'YAML'
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
fi

# Clean GUI work/spec and old bundle (keep other dist outputs)
rm -rf build/gui build/spec/Autobuild_Desktop "dist/Autobuild Desktop.app"

# Build the Tk GUI as a .app bundle with pywebview bundled
pyinstaller \
  --name "Autobuild Desktop" \
  --windowed \
  --clean --noconfirm \
  --distpath dist \
  --workpath build/gui \
  --specpath build/spec/Autobuild_Desktop \
  --hidden-import webview \
  --hidden-import webview.platforms.cocoa \
  --collect-data webview \
  --collect-all webview \
  "$ENTRY"

echo
echo "✅ Built: dist/Autobuild Desktop.app"
echo "Run with logs:"
echo "  \"dist/Autobuild Desktop.app/Contents/MacOS/Autobuild Desktop\""
echo "Or simply open:"
echo "  open \"dist/Autobuild Desktop.app\""
