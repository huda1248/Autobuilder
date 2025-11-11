from __future__ import annotations
import os, sys, subprocess, threading, queue
from pathlib import Path
import yaml

from PySide6.QtCore import Qt, QUrl, QProcess, QTimer
from PySide6.QtGui import QAction, QFont, QTextOption
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QSplitter, QFileSystemModel, QTreeView,
    QPlainTextEdit, QLineEdit, QToolBar, QLabel, QPushButton, QHBoxLayout,
    QVBoxLayout, QFileDialog, QMessageBox, QSizePolicy, QTabWidget
)
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT = Path.cwd()
CONFIG = ROOT / "config" / "autobuild.yml"
CUR = ROOT / ".autobuild_current"

def cfg():
    try:
        return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:
        return {"projects":[]}

def projects():
    out = []
    for p in cfg().get("projects", []):
        name = p.get("name") or "Autobuilder"
        path = Path(p.get("path",".")).expanduser().resolve()
        out.append((name, path))
    return out or [("Autobuilder", ROOT)]

def write_cur(p: Path): CUR.write_text(str(p), encoding="utf-8")
def read_cur() -> Path:
    try: return Path(CUR.read_text(encoding="utf-8").strip()).expanduser().resolve()
    except Exception: return ROOT

class Editor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Menlo", 12))
        self.setWordWrapMode(QTextOption.NoWrap)
        self._path: Path|None = None

    def load(self, p: Path):
        try:
            txt = p.read_text(encoding="utf-8")
            self.setPlainText(txt)
            self._path = p
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))

    def save(self):
        if not self._path:
            f, _ = QFileDialog.getSaveFileName(self, "Save file as")
            if not f: return
            self._path = Path(f)
        self._path.write_text(self.toPlainText(), encoding="utf-8")

class Console(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Menlo", 11))
        self.setMaximumHeight(220)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def write(self, s: str):
        self.moveCursor(self.textCursor().End)
        self.insertPlainText(s)
        self.moveCursor(self.textCursor().End)

def run_stream(cmd: str, cwd: Path, out: Console):
    def worker():
        out.write(f"> {cmd}\n(in {cwd})\n")
        proc = subprocess.Popen(["bash","-lc", cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert proc.stdout
        for line in proc.stdout:
            out.write(line)
        rc = proc.wait()
        out.write(f"[exit {rc}]\n\n")
    threading.Thread(target=worker, daemon=True).start()

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Autobuild Desktop (Qt)")
        self.resize(1400, 900)

        self.projs = dict(projects())
        self.active: Path = read_cur()
        if self.active not in self.projs.values():
            self.active = next(iter(self.projs.values()))
            write_cur(self.active)

        # Toolbar
        tb = QToolBar(); self.addToolBar(tb)
        tb.setMovable(False)

        tb.addWidget(QLabel("Active: "))
        self.active_lbl = QLabel(str(self.active)); tb.addWidget(self.active_lbl)

        tb.addSeparator(); tb.addWidget(QLabel(" Commit msg "))
        self.cmsg = QLineEdit("assistant update"); self.cmsg.setFixedWidth(320); tb.addWidget(self.cmsg)

        act_save   = QAction("Save", self);   act_save.triggered.connect(self.save_current);   tb.addAction(act_save)
        act_commit = QAction("Commit", self); act_commit.triggered.connect(self.git_commit);   tb.addAction(act_commit)
        act_push   = QAction("Push", self);   act_push.triggered.connect(lambda: self.run("git push || true")); tb.addAction(act_push)

        tb.addSeparator(); tb.addWidget(QLabel(" API Port "))
        self.api = QLineEdit("8080"); self.api.setFixedWidth(80); tb.addWidget(self.api)
        act_api  = QAction("Start/Stop API", self); act_api.triggered.connect(self.toggle_api); tb.addAction(act_api)

        # Splitters
        outer = QSplitter(Qt.Vertical); self.setCentralWidget(outer)
        top   = QSplitter(Qt.Horizontal); outer.addWidget(top)
        self.console = Console(); outer.addWidget(self.console)
        outer.setStretchFactor(0, 1); outer.setStretchFactor(1, 0)

        # Left: file tree
        self.fs = QFileSystemModel(); self.fs.setRootPath(str(self.active))
        self.fs.setFilter(self.fs.filter() | self.fs.Dirs | self.fs.Files)
        self.tree = QTreeView(); self.tree.setModel(self.fs)
        self.tree.setRootIndex(self.fs.index(str(self.active)))
        self.tree.doubleClicked.connect(self.open_from_tree)
        self.tree.setColumnWidth(0, 260)
        top.addWidget(self.tree)

        # Middle: editor
        self.editor = Editor(); top.addWidget(self.editor)

        # Right: tabs (ChatGPT web + API chat)
        self.tabs = QTabWidget(); top.addWidget(self.tabs)

        self.web = QWebEngineView()
        self.web.setUrl(QUrl("https://chatgpt.com"))   # embedded website
        self.tabs.addTab(self.web, "ChatGPT (web)")

        # API chat tab (optional)
        self.chat = QWidget(); self.tabs.addTab(self.chat, "Assistant (API)")
        v = QVBoxLayout(self.chat)
        self.chat_log = QPlainTextEdit(); self.chat_log.setReadOnly(True); self.chat_log.setMaximumBlockCount(5000)
        self.chat_input = QLineEdit()
        btn = QPushButton("Send")
        row = QHBoxLayout(); row.addWidget(self.chat_input); row.addWidget(btn)
        v.addWidget(self.chat_log); v.addLayout(row)
        btn.clicked.connect(self.send_api)

        # Final wiring
        self._api_proc: subprocess.Popen[str] | None = None
        self.console.write("Qt Trae-like UI loaded.\n")

    # Slots
    def open_from_tree(self, idx):
        p = Path(self.fs.filePath(idx))
        if p.is_file():
            self.editor.load(p)

    def save_current(self):
        self.editor.save()

    def git_commit(self):
        msg = self.cmsg.text().strip() or "assistant update"
        self.run(f'git add -A && git commit -m "{msg}" || true')

    def run(self, bash_cmd: str):
        run_stream(bash_cmd, self.active, self.console)

    def toggle_api(self):
        if self._api_proc and self._api_proc.poll() is None:
            self._api_proc.terminate(); self._api_proc = None
            self.console.write("API stopped\n"); return
        port = self.api.text().strip() or "8080"
        self._api_proc = subprocess.Popen(["bash","-lc", f"python -m http.server {port}"], cwd=str(self.active),
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        def pump():
            for line in self._api_proc.stdout:  # type: ignore
                self.console.write(line)
        threading.Thread(target=pump, daemon=True).start()
        self.console.write(f"API started at http://localhost:{port}\n")

    # --- OpenAI API chat (optional) ---
    def _client(self):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            return None
        try:
            from openai import OpenAI
            return OpenAI(api_key=key)
        except Exception:
            return None

    def send_api(self):
        text = self.chat_input.text().strip()
        if not text: return
        self.chat_input.clear()
        self.chat_log.appendPlainText(f"You: {text}")
        client = self._client()
        if not client:
            self.chat_log.appendPlainText("(No OPENAI_API_KEY set)")
            return
        q: queue.Queue[str] = queue.Queue()

        def worker():
            try:
                try:
                    resp = client.chat.completions.create(
                        model=os.getenv("AUTOBUILD_MODEL","gpt-4o-mini"),
                        messages=[{"role":"system","content":"You assist with code edits and git operations."},
                                  {"role":"user","content":text}],
                        temperature=0.2,
                    )
                except AttributeError:
                    resp = client.chat_completions.create(
                        model=os.getenv("AUTOBUILD_MODEL","gpt-4o-mini"),
                        messages=[{"role":"system","content":"You assist with code edits and git operations."},
                                  {"role":"user","content":text}],
                        temperature=0.2,
                    )
                msg = resp.choices[0].message
                content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "")
                q.put(content or "")
            except Exception as e:
                q.put(f"[ERROR] {e}")

        threading.Thread(target=worker, daemon=True).start()

        def pump():
            try:
                ans = q.get_nowait()
                self.chat_log.appendPlainText(f"Assistant: {ans}")
            except queue.Empty:
                QTimer.singleShot(60, pump)
        QTimer.singleShot(60, pump)

def main():
    app = QApplication(sys.argv)
    win = Main(); win.show()
    sys.exit(app.exec())
if __name__ == "__main__":
    main()
