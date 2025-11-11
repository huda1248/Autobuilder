#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
cd "$(dirname "$0")/.."

# Detect entry (supports either tools/… or repo root)
if [[ -f tools/autobuild_textual.py ]]; then
  ENTRY="tools/autobuild_textual.py"
elif [[ -f autobuild_textual.py ]]; then
  ENTRY="autobuild_textual.py"
else
  echo "❌ Could not find autobuild_textual.py (tools/ or root)."
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

# Clean CLI work/spec and just the previous binary
rm -rf build/cli build/spec/AutobuildTerminal dist/AutobuildTerminal

# Build the Textual TUI single-file binary (bundle rich/textual/webview assets)
pyinstaller \
  --onefile \
  --name "AutobuildTerminal" \
  --clean --noconfirm \
  --distpath dist \
  --workpath build/cli \
  --specpath build/spec/AutobuildTerminal \
  --hidden-import webview \
  --hidden-import webview.platforms.cocoa \
  --collect-data webview \
  --collect-all webview \
  --collect-all textual \
  --collect-all rich \
  "$ENTRY"

echo
echo "✅ Built: dist/AutobuildTerminal"
echo "Run:"
echo "  ./dist/AutobuildTerminal"
