#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Pick GUI entry (Qt preferred, Tk fallback) ---
SCRIPT=""
USING_QT=0
if [ -f tools/autobuild_desktop_qt.py ]; then
  SCRIPT="tools/autobuild_desktop_qt.py"
  USING_QT=1
elif [ -f tools/autobuild_desktop_tk.py ]; then
  SCRIPT="tools/autobuild_desktop_tk.py"
else
  echo "ERROR: No GUI entry file found."
  echo "  Expected: tools/autobuild_desktop_qt.py or tools/autobuild_desktop_tk.py"
  exit 1
fi
echo "Using GUI entry: ${SCRIPT}"

# --- Hard clean (prevents Qt symlink collisions) ---
pkill -f "Autobuild Desktop" >/dev/null 2>&1 || true
rm -rf "dist/Autobuild Desktop.app" dist build/gui_qt build/spec/Autobuild_Qt \
  "$HOME/Library/Application Support/pyinstaller"
find . -name "*.spec" -delete

# --- Ensure minimal config ---
mkdir -p config
test -f config/autobuild.yml || cat > config/autobuild.yml <<'YAML'
project_name: "Autobuilder"
projects:
  - { name: "Autobuilder", path: "." }
YAML

# --- Common flags ---
COMMON=(
  --name "Autobuild Desktop"
  --windowed
  --noconfirm --clean
  --distpath dist
  --workpath build/gui_qt
  --specpath build/spec/Autobuild_Qt
)

if [ "${USING_QT}" = "1" ]; then
  echo "Building Qt/WebEngine bundle (focused include; exclude 3D/QML)…"

  QT_FLAGS=(
    # Core widgets + webengine
    --hidden-import PySide6.QtCore
    --hidden-import PySide6.QtGui
    --hidden-import PySide6.QtWidgets
    --hidden-import PySide6.QtWebEngineWidgets
    --hidden-import PySide6.QtWebChannel

    # A few common extras (safe)
    --hidden-import PySide6.QtNetwork
    --hidden-import PySide6.QtPrintSupport
    --hidden-import PySide6.QtSvg
    --hidden-import PySide6.QtSvgWidgets
    --hidden-import PySide6.QtOpenGL
    --hidden-import PySide6.QtOpenGLWidgets
    --hidden-import PySide6.QtWebSockets
    --hidden-import PySide6.QtPdf
    --hidden-import PySide6.QtPdfWidgets

    # WebEngine runtime deps (targeted)
    --collect-submodules PySide6.QtWebEngineWidgets
    --collect-binaries   PySide6.QtWebEngineCore
    --copy-metadata      PySide6

    # EXCLUDE stacks that cause collisions or pull QML/3D
    --exclude-module PySide6.Qt3DAnimation
    --exclude-module PySide6.Qt3DCore
    --exclude-module PySide6.Qt3DRender
    --exclude-module PySide6.Qt3DExtras
    --exclude-module PySide6.Qt3DInput
    --exclude-module PySide6.Qt3DLogic

    # Not using QML/Quick/Quick3D/Designer: exclude to avoid DesignHelpers noise
    --exclude-module PySide6.QtQml
    --exclude-module PySide6.QtQuick
    --exclude-module PySide6.QtQuickWidgets
    --exclude-module PySide6.QtQuick3D
    --exclude-module PySide6.QtDesigner
    --exclude-module PySide6.QtGraphs
    --exclude-module PySide6.QtGraphsWidgets

    # Avoid shipping SQL/Multimedia if not needed (uncomment to include)
    # --hidden-import PySide6.QtSql
    # --hidden-import PySide6.QtMultimedia
    # --hidden-import PySide6.QtMultimediaWidgets
  )

  pyinstaller "${COMMON[@]}" "${QT_FLAGS[@]}" "$SCRIPT"
else
  echo "Qt entry not found; building Tk (pywebview) bundle instead…"
  TK_FLAGS=(
    --hidden-import webview
    --hidden-import webview.platforms.cocoa
    --collect-data webview
  )
  pyinstaller "${COMMON[@]}" "${TK_FLAGS[@]}" "$SCRIPT"
fi

echo
echo "✅ Built: dist/Autobuild Desktop.app"
echo 'Run with logs: "./dist/Autobuild Desktop.app/Contents/MacOS/Autobuild Desktop"'
