# tools/autobuild_desktop_tk.py
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# NEW: embed real chatgpt.com in a native WebKit window
import webview  # pip install pywebview

# ---------- repo paths ----------
ROOT = Path.cwd()
CONFIG = ROOT / "config" / "autobuild.yml"
CUR = ROOT / ".autobuild_current"

# ---------- config & project helpers ----------
def cfg():
    try:
        import yaml
        return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:
        return {"projects": []}

def projects():
    return [(p.get("name"), Path(p["path"]).expanduser().resolve())
            for p in cfg().get("projects", []) if p.get("name") and p.get("path")]

def write_cur(p: Path):
    CUR.write_text(str(p), encoding="utf-8")

def read_cur() -> Path:
    try:
        return Path(CUR.read_text(encoding="utf-8").strip()).expanduser().resolve()
    except Exception:
        return ROOT

# ---------- process streaming ----------
def run_stream(cmd, cwd, out_text: tk.Text):
    """Run a command and stream stdout/stderr to a tk.Text widget."""
    def worker():
        out_text.insert("end", f"> {' '.join(cmd)}   (in {cwd})\n")
        out_text.see("end")
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            out_text.insert("end", line)
            out_text.see("end")
        proc.wait()
        out_text.insert("end", f"\n[exit {proc.returncode}]\n\n")
        out_text.see("end")
    threading.Thread(target=worker, daemon=True).start()

HELP = """\
Slash-like actions in Desktop:
- Use the buttons below to scaffold, apply patches, commit & push.
- For full shell access, use the Terminal or the TUI binary.
"""

# ---------- the Tk app ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Build tag (you can SEE fresh builds)
        build_tag = f"{Path(__file__).name} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.title(f"Autobuild Desktop — {build_tag}")
        self.geometry("1080x700")

        # Projects & active path
        self.projs = dict(projects()) or {"Autobuilder": ROOT}
        self.active = read_cur() if read_cur() in self.projs.values() else next(iter(self.projs.values()))
        self.cfg = cfg()

        # Top bar
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Label(top, text="Project").pack(side="left")
        self.choice = tk.StringVar(value=next(iter(self.projs.keys())))
        self.combo = ttk.Combobox(top, textvariable=self.choice, values=list(self.projs.keys()),
                                  width=28, state="readonly")
        self.combo.pack(side="left", padx=6)
        ttk.Button(top, text="Use", command=self.use_project).pack(side="left")

        ttk.Label(top, text="Active:").pack(side="left", padx=12)
        self.active_lbl = ttk.Label(top, text=str(self.active), foreground="green")
        self.active_lbl.pack(side="left", padx=4)

        # NEW: Open ChatGPT (real chatgpt.com in a webview)
        ttk.Button(top, text="Open ChatGPT", command=self.open_chatgpt).pack(side="right", padx=6)

        # Build tag banner
        banner = ttk.Frame(self)
        banner.pack(fill="x", padx=8)
        ttk.Label(banner, text="✅ Fresh build running", font=("Helvetica", 14)).pack(anchor="w")
        ttk.Label(banner, text=f"__file__: {__file__}", wraplength=1000).pack(anchor="w")
        ttk.Label(banner, text=f"cwd: {Path.cwd()}").pack(anchor="w", pady=(0, 6))

        # Notebook (tabs)
        nb = ttk.Notebook(self)
        nb.pack(fill="x", padx=8)

        # Scaffold tab
        scf = ttk.Frame(nb)
        nb.add(scf, text="Scaffold")
        ttk.Label(scf, text="Name").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.sc_name = ttk.Entry(scf, width=24)
        self.sc_name.insert(0, "hello_world")
        self.sc_name.grid(row=0, column=1, sticky="w")
        ttk.Label(scf, text="Out").grid(row=0, column=2, padx=6, sticky="w")
        self.sc_out = ttk.Entry(scf, width=24)
        self.sc_out.insert(0, "./out_cli")
        self.sc_out.grid(row=0, column=3, sticky="w")
        ttk.Button(scf, text="Run Scaffold", command=self.do_scaffold)\
            .grid(row=0, column=4, padx=6, sticky="w")

        # Patch / Commit / Push controls
        gf = ttk.Frame(self)
        gf.pack(fill="x", padx=8, pady=4)

        ttk.Label(gf, text="Patch file").grid(row=0, column=0, sticky="w")
        self.patch = ttk.Entry(gf, width=60)
        self.patch.grid(row=0, column=1, padx=6, sticky="we")
        ttk.Button(gf, text="Browse…", command=self.pick_patch).grid(row=0, column=2)
        ttk.Button(gf, text="Apply Patch", command=self.do_patch).grid(row=0, column=3, padx=6)

        ttk.Label(gf, text="Commit msg").grid(row=1, column=0, sticky="w", pady=4)
        self.commit_msg = ttk.Entry(gf, width=60)
        self.commit_msg.insert(0, "assistant update")
        self.commit_msg.grid(row=1, column=1, padx=6, sticky="we")

        ttk.Label(gf, text="API Port").grid(row=1, column=2, sticky="e")
        self.api_port = ttk.Entry(gf, width=8)
        self.api_port.insert(0, "8080")
        self.api_port.grid(row=1, column=3, sticky="w")
        ttk.Button(gf, text="Start/Stop API", command=self.start_api).grid(row=1, column=4, padx=6, sticky="w")

        # Git actions row (Commit / Push / PR)
        btns = ttk.Frame(gf)
        btns.grid(row=2, column=0, columnspan=5, sticky="w", pady=(6, 0))
        def _run(cmd):
            run_stream(["bash","-lc", cmd], cwd=str(self.active), out_text=self.out)
        ttk.Button(btns, text="Commit", command=lambda:_run(
            f'git add -A && git commit -m "{self.commit_msg.get().strip() or "assistant: update"}" || true'
        )).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="Push", command=lambda:_run('git push || true')).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="Open PR", command=lambda:_run('gh pr create --fill || gh pr view --web || true')).pack(side="left", padx=(0,6))

        # Console output (streamed)
        out_frame = ttk.Frame(self)
        out_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.out = tk.Text(out_frame, height=18)
        self.out.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(out_frame, orient="vertical", command=self.out.yview)
        sb.pack(side="right", fill="y")
        self.out.configure(yscrollcommand=sb.set)
        self.out.insert("end", HELP + "\n")

    # ---------- actions ----------
    def use_project(self):
        name = self.choice.get()
        path = self.projs.get(name, ROOT)
        self.active = path
        write_cur(path)
        self.active_lbl.config(text=str(path))
        self.out.insert("end", f"✔ Active project set to: {name} -> {path}\n")
        self.out.see("end")

    def do_scaffold(self):
        name = self.sc_name.get().strip()
        out_dir = self.sc_out.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Please enter a scaffold name.")
            return
        cmd = [
            "bash", "-lc",
            f'mkdir -p "{out_dir}" && '
            f'echo "print(\'hello from {name}\')" > "{out_dir}/{name}.py" && '
            f'ls -la "{out_dir}"'
        ]
        run_stream(cmd, cwd=str(self.active), out_text=self.out)

    def pick_patch(self):
        p = filedialog.askopenfilename(title="Choose a patch file", initialdir=str(self.active))
        if p:
            self.patch.delete(0, "end")
            self.patch.insert(0, p)

    def do_patch(self):
        patch_path = self.patch.get().strip()
        msg = self.commit_msg.get().strip() or "assistant: update"
        if not patch_path:
            messagebox.showerror("No patch", "Select a patch file first.")
            return
        cmd = ["bash", "-lc", f'git apply "{patch_path}" --reject --whitespace=fix && git add -A && git commit -m "{msg}" || true']
        run_stream(cmd, cwd=str(self.active), out_text=self.out)

    def start_api(self):
        # toggle start/stop simple demo server
        if getattr(self, "_api_proc", None) and self._api_proc.poll() is None:
            self._api_proc.terminate()
            self.out.insert("end", "🛑 API stopped\n"); self.out.see("end")
            self._api_proc = None
            return
        port = self.api_port.get().strip() or "8080"
        self._api_proc = subprocess.Popen(
            ["python","-m","http.server", port],
            cwd=str(self.active),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        def pump():
            for line in self._api_proc.stdout:  # type: ignore
                self.out.insert("end", line); self.out.see("end")
        threading.Thread(target=pump, daemon=True).start()
        self.out.insert("end", f"🚀 API started on http://localhost:{port}\n"); self.out.see("end")

    # ---------- NEW: open ChatGPT (chatgpt.com) ----------
    def open_chatgpt(self):
        # Launch webview on a background thread so Tk stays responsive
        def _run():
            webview.create_window(
                title="ChatGPT",
                url="https://chatgpt.com",
                width=1200,
                height=800,
                resizable=True,
                confirm_close=False,
                easy_drag=False,
            )
            # Explicitly choose Cocoa backend on macOS
            webview.start(gui='cocoa')
        threading.Thread(target=_run, daemon=True).start()

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
