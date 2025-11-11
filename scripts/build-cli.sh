#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Ensure default config exists
if [ ! -f config/autobuild.yml ]; then
  echo "Creating default config/autobuild.yml"
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

# Clean only CLI work/spec paths (NOT dist/)
rm -rf build/cli build/spec/AutobuildTerminal

pyinstaller \
  --onefile \
  --name "AutobuildTerminal" \
  --distpath dist \
  --workpath build/cli \
  --specpath build/spec/AutobuildTerminal \
  tools/autobuild_textual.py

echo
echo "✅ Built: dist/AutobuildTerminal"
echo "Run test: ./dist/AutobuildTerminal --help || ./dist/AutobuildTerminal"
