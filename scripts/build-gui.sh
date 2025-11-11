#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Find the GUI entry file ---
SCRIPT=""
if [ -f tools/autobuild_desktop_qt.py ]; then
  SCRIPT="tools/autobuild_desktop_qt.py"
elif [ -f tools/autobuild_desktop_tk.py ]; then
  SCRIPT="tools/autobuild_desktop_tk.py"
else
  echo "ERROR: No GUI entry file found. Expected one of:"
  echo "  - tools/autobuild_desktop_qt.py"
  echo "  - tools/autobuild_desktop_tk.py"
  exit 1
fi
echo "Using GUI entry: ${SCRIPT}"

# --- Hard clean to avoid stale Qt symlink collisions ---
pkill -f "Autobuild Desktop" >/dev/null 2>&1 || true
rm -rf dist build/gui_qt build/spec/Autobuild_Qt \
  "$HOME/Library/Application Support/pyinstaller"
find . -name "*.spec" -delete

# Minimal config (idempotent)
mkdir -p config
test -f config/autobuild.yml || cat > config/autobuild.yml <<'YAML'
project_name: "Autobuilder"
projects:
  - { name: "Autobuilder", path: "." }
YAML

# --- Common PyInstaller flags ---
COMMON=( \
  --name "Autobuild Desktop" \
  --windowed \
  --noconfirm --clean \
  --distpath dist \
  --workpath build/gui_qt \
  --specpath build/spec/Autobuild_Qt \
)

# If Qt version is used, include WebEngine bits and exclude Qt3D (avoids mac symlink crash)
if [[ "${SCRIPT}" == tools/autobuild_desktop_qt.py ]]; then
  echo "Building Qt/WebEngine bundle…"
  pyinstaller \
    "${COMMON[@]}" \
# core widgets + webengine
--hidden-import PySide6.QtCore \
--hidden-import PySide6.QtGui \
--hidden-import PySide6.QtWidgets \
--hidden-import PySide6.QtWebEngineWidgets \
--hidden-import PySide6.QtWebChannel \
\
# “more of Qt” you may want available
--hidden-import PySide6.QtNetwork \
--hidden-import PySide6.QtPrintSupport \
--hidden-import PySide6.QtSvg \
--hidden-import PySide6.QtSvgWidgets \
--hidden-import PySide6.QtSql \
--hidden-import PySide6.QtMultimedia \
--hidden-import PySide6.QtMultimediaWidgets \
--hidden-import PySide6.QtOpenGL \
--hidden-import PySide6.QtOpenGLWidgets \
--hidden-import PySide6.QtWebSockets \
--hidden-import PySide6.QtPdf \
--hidden-import PySide6.QtPdfWidgets \
--hidden-import PySide6.QtQuick \
--hidden-import PySide6.QtQuickWidgets \
\
# data & binaries for WebEngine (keeps the app working)
--collect-data PySide6 \
--collect-submodules PySide6.QtWebEngineWidgets \
--collect-binaries PySide6.QtWebEngineCore \
\
# EXCLUDE ONLY the Qt3D stack — this avoids the duplicate symlink crash
--exclude-module PySide6.Qt3DAnimation \
--exclude-module PySide6.Qt3DCore \
--exclude-module PySide6.Qt3DRender \
--exclude-module PySide6.Qt3DExtras \
--exclude-module PySide6.Qt3DInput \
--exclude-module PySide6.Qt3DLogic \

    "${SCRIPT}"
else
  echo "Building Tk (pywebview) bundle…"
  pyinstaller \
    "${COMMON[@]}" \
    --hidden-import webview \
    --hidden-import webview.platforms.cocoa \
    --collect-data webview \
    "${SCRIPT}"
fi

echo
echo "✅ Built: dist/Autobuild Desktop.app"
echo 'Run with logs: "./dist/Autobuild Desktop.app/Contents/MacOS/Autobuild Desktop"'
