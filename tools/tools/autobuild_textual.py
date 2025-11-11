from __future__ import annotations
import asyncio, os, sys, shlex, threading
from pathlib import Path
import yaml

# NEW: real ChatGPT window
try:
    import webview  # pip install pywebview
    _WEBVIEW_OK = True
except Exception:
    _WEBVIEW_OK = False

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, TextLog, Input, Button, Select, Label
from textual.containers import Horizontal

ROOT = Path.cwd()
CFG = ROOT / "config" / "autobuild.yml"
CUR = ROOT / ".autobuild_current"

def load_projects() -> list[tuple[str, Path]]:
    try:
        cfg = yaml.safe_load(CFG.read_text()) or {}
        items = []
        for p in cfg.get("projects", []):
            name = p.get("name") or "Unnamed"
            path = Path(p["path"]).expanduser().resolve()
            items.append((name, path))
        return items or [("Autobuilder", ROOT)]
    except Exception:
        return [("Autobuilder", ROOT)]

def write_current(p: Path) -> None:
    CUR.write_text(str(p), encoding="utf-8")

def read_current() -> Path:
    try:
        return Path(CUR.read_text().strip()).expanduser().resolve()
    except Exception:
        return ROOT

class Toolbar(Horizontal):
    def compose(self) -> ComposeResult:
        projs = load_projects()
        yield Label("Project")
        yield Select(((n, n) for n,_ in projs), id="proj-select")
        yield Button("Use", id="use")
        yield Static(id="active", classes="active")
        yield Button("Scaffold", id="scaffold")
        yield Input(placeholder="name (e.g., hello_world)", id="sc-name")
        yield Input(placeholder="out dir (e.g., ./out_cli)", id="sc-out")
        # NEW: ChatGPT button to open chatgpt.com in a native window
        yield Button("ChatGPT", id="chatgpt")

class GitBar(Horizontal):
    def compose(self) -> ComposeResult:
        yield Input(placeholder="patch file path", id="patch")
        yield Button("Apply Patch", id="patch-apply")
        yield Input(placeholder="commit message", id="cmsg", value="assistant update")
        yield Button("Commit", id="commit")
        yield Button("Push", id="push")
        yield Button("Open PR", id="pr")
        yield Button("Status", id="status")

class ApiBar(Horizontal):
    def compose(self) -> ComposeResult:
        yield Label("API Port")
        yield Input(value="8080", id="port", classes="narrow")
        yield Button("Start API", id="api-start")

class AutobuildApp(App):
    CSS = """
    Screen { layout: vertical; }
    .active { color: green; height: 1; padding-left: 1; }
    .narrow { width: 10; }
    #log { height: 1fr; border: solid $accent; }
    """

    active_path: reactive[Path] = reactive(read_current())

    def compose(self) -> ComposeResult:
        yield Header(name="Autobuild Terminal")
        yield Toolbar()
        yield GitBar()
        yield ApiBar()
        yield TextLog(id="log", highlight=True, wrap=False)
        yield Footer()

    def log(self, msg: str) -> None:
        self.query_one(TextLog).write(msg.rstrip("\n"))

    async def run_stream(self, cmd: list[str], cwd: Path) -> int:
        self.log(f"> {' '.join(shlex.quote(c) for c in cmd)}   (in {cwd})\n")
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING":"utf-8"},
        )
        assert proc.stdout
        async for line in proc.stdout:
            try:
                self.log(line.decode() if isinstance(line, (bytes, bytearray)) else line)
            except Exception:
                self.log(str(line))
        rc = await proc.wait()
        self.log(f"[exit {rc}]\n\n")
        return rc

    def _projects_map(self) -> dict[str, Path]:
        return {n: p for n, p in load_projects()}

    def on_mount(self) -> None:
        projs = self._projects_map()
        sel = self.query_one("#proj-select", Select)
        sel.set_options([(n, n) for n in projs.keys()])
        sel.value = next(iter(projs.keys()))
        self.query_one("#active", Static).update(str(self.active_path))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "use":
            projs = self._projects_map()
            name = self.query_one("#proj-select", Select).value
            p = projs.get(name)
            if not p or not p.exists():
                self.log(f"[ERROR] path not found: {p}\n"); return
            self.active_path = p
            write_current(p)
            self.query_one("#active", Static).update(str(p))
            self.log(f"[OK] Active project -> {p}\n"); return

        if bid == "scaffold":
            name = self.query_one("#sc-name", Input).value or "hello_world"
            out  = self.query_one("#sc-out",  Input).value or "./out_cli"
            await self.run_stream(["autobuilder","--name",name,"--out",out], self.active_path); return

        if bid == "patch-apply":
            patch = self.query_one("#patch", Input).value.strip()
            if not patch: self.log("[WARN] choose a patch file\n"); return
            await self.run_stream([sys.executable,"tools/patcher.py",patch], self.active_path); return

        if bid == "commit":
            msg = self.query_one("#cmsg", Input).value or "assistant update"
            await self.run_stream([sys.executable,"tools/autobuild_term.py","commit","-m",msg], self.active_path); return

        if bid == "push":
            await self.run_stream([sys.executable,"tools/autobuild_term.py","push"], self.active_path); return

        if bid == "pr":
            await self.run_stream([sys.executable,"tools/autobuild_term.py","pr"], self.active_path); return

        if bid == "status":
            await self.run_stream(["git","status"], self.active_path); return

        if bid == "api-start":
            port = (self.query_one("#port", Input).value or "8080").strip()
            helper = self.active_path / "scripts" / "free-port-8080.sh"
            if helper.exists():
                await self.run_stream([str(helper)], self.active_path)
            await self.run_stream(["uvicorn","autoappbuilder.api.app:app","--reload","--port",port], self.active_path); return

        # NEW: open ChatGPT in a native WebKit window (via pywebview)
        if bid == "chatgpt":
            if not _WEBVIEW_OK:
                self.log("[ERROR] pywebview not installed. Run: python -m pip install pywebview\n")
                return
            def _open():
                try:
                    webview.create_window(
                        "ChatGPT",
                        "https://chatgpt.com",
                        width=1200,
                        height=800,
                    )
                    # Explicit Cocoa backend for macOS
                    webview.start(gui='cocoa')
                except Exception as e:
                    self.log(f"[ERROR] webview failed: {e}\n")
            threading.Thread(target=_open, daemon=True).start()
            self.log("🌐 ChatGPT window opened.\n")
            return

if __name__ == "__main__":
    AutobuildApp().run()
