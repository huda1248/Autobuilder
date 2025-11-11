# tools/autobuild_desktop_tk.py
from __future__ import annotations
import os, sys, subprocess, threading, queue
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml

try:
    import webview
    _HAS_WEBVIEW = True
except Exception:
    _HAS_WEBVIEW = False

try:
    from openai import OpenAI
    _OPENAI_KEY = os.environ.get("OPENAI_API_KEY") or ""
    _HAS_OPENAI = bool(_OPENAI_KEY)
except Exception:
    _HAS_OPENAI = False
    _OPENAI_KEY = ""

ROOT = Path.cwd()
CONFIG = ROOT / "config" / "autobuild.yml"
CUR = ROOT / ".autobuild_current"

def cfg():
    try:
        return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    except Exception:
        return {"projects": []}

def projects():
    projs = []
    for p in cfg().get("projects", []):
        name = p.get("name"); path = p.get("path")
        if name and path:
            projs.append((name, Path(path).expanduser().resolve()))
    return projs or [("Autobuilder", ROOT)]

def write_cur(p: Path): CUR.write_text(str(p), encoding="utf-8")
def read_cur() -> Path:
    try: return Path(CUR.read_text(encoding="utf-8").strip()).expanduser().resolve()
    except Exception: return ROOT

def run_stream(cmd: str, cwd: Path, out: tk.Text):
    def worker():
        out.insert("end", f"> {cmd}\n(in {cwd})\n"); out.see("end")
        proc = subprocess.Popen(["bash","-lc", cmd], cwd=cwd,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert proc.stdout
        for line in proc.stdout:
            out.insert("end", line); out.see("end")
        proc.wait()
        out.insert("end", f"[exit {proc.returncode}]\n\n"); out.see("end")
    threading.Thread(target=worker, daemon=True).start()

class CodeEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.path: Path | None = None
        self._dirty = tk.BooleanVar(value=False)
        top = ttk.Frame(self); top.pack(fill="x")
        self.title = ttk.Label(top, text="(no file)", font=("Menlo", 11, "bold"))
        self.title.pack(side="left", padx=6, pady=6)
        ttk.Button(top, text="Open…", command=self.open_file).pack(side="right", padx=3)
        ttk.Button(top, text="Save", command=self.save_file).pack(side="right", padx=3)
        wrap = ttk.Frame(self); wrap.pack(fill="both", expand=True)
        self.text = tk.Text(wrap, undo=True, wrap="none", font=("Menlo", 12))
        self.text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)
        self.text.bind("<<Modified>>", self._on_modified)
    def _on_modified(self, _):
        self.text.edit_modified(False); self._dirty.set(True); self._update_title()
    def _update_title(self):
        name = self.path.name if self.path else "(no file)"
        self.title.configure(text=f"{name}{' •' if self._dirty.get() else ''}")
    def load(self, p: Path):
        self.path = p
        txt = p.read_text(encoding="utf-8")
        self.text.delete("1.0", "end"); self.text.insert("1.0", txt)
        self._dirty.set(False); self._update_title()
    def open_file(self):
        p = filedialog.askopenfilename(title="Open file", initialdir=str(self.path.parent if self.path else "."))
        if p: self.load(Path(p))
    def save_file(self):
        if not self.path:
            p = filedialog.asksaveasfilename(title="Save file as")
            if not p: return
            self.path = Path(p)
        self.path.write_text(self.text.get("1.0","end-1c"), encoding="utf-8")
        self._dirty.set(False); self._update_title()

class FolderTree(ttk.Frame):
    def __init__(self, master, on_open):
        super().__init__(master); self.on_open = on_open
        self.tree = ttk.Treeview(self, columns=("full",), displaycolumns=()); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewOpen>>", self._expand); self.tree.bind("<Double-1>", self._open)
    def populate(self, root: Path):
        self.tree.delete(*self.tree.get_children())
        root_id = self.tree.insert("", "end", text=str(root), values=(str(root),), open=True)
        self._add_children(root_id, root)
    def _add_children(self, parent_id, path: Path):
        for p in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if p.name.startswith(".git"): continue
            node = self.tree.insert(parent_id, "end", text=p.name, values=(str(p),))
            if p.is_dir(): self.tree.insert(node, "end", text="…", values=(str(p/"__placeholder__"),))
    def _expand(self, _):
        node = self.tree.focus()
        for c in self.tree.get_children(node):
            if self.tree.item(c, "text") == "…": self.tree.delete(c)
        full = Path(self.tree.set(node, "full")); self._add_children(node, full)
    def _open(self, _):
        node = self.tree.focus()
        if not node: return
        full = Path(self.tree.set(node, "full"))
        if full.is_file(): self.on_open(full)

class ChatPane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="Chat", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=6, pady=4)
        self.log = tk.Text(self, height=18, wrap="word"); self.log.pack(fill="both", expand=True, padx=6)
        row = ttk.Frame(self); row.pack(fill="x", padx=6, pady=6)
        self.entry = ttk.Entry(row); self.entry.pack(side="left", fill="x", expand=True, padx=(0,6))
        ttk.Button(row, text="Send", command=self.send).pack(side="left")
        self.client = OpenAI(api_key=_OPENAI_KEY) if (_HAS_OPENAI) else None
        if not _HAS_OPENAI:
            self.log.insert("end", "No OPENAI_API_KEY set.\n")
            if _HAS_WEBVIEW:
                ttk.Button(self, text="Open ChatGPT (web)", command=self.open_web).pack(padx=6, pady=(0,8))
            else:
                self.log.insert("end", "Tip: pip install pywebview\n")
    ## PATCHED
def open_web(self):
        def _run():
            webview.create_window("ChatGPT", "https://chatgpt.com", width=1200, height=800)
            webview.start(gui='cocoa')
        # Launch helper process so Cocoa runs on its own main thread
helper = '''
import webview
webview.create_window("ChatGPT", "https://chatgpt.com", width=1200, height=800)
webview.start(gui="cocoa")
'''
subprocess.Popen([sys.executable, "-c", helper])
    def send(self):
        text = self.entry.get().strip()
        if not text: return
        self.entry.delete(0,"end"); self.log.insert("end", f"🧑‍💻 You: {text}\n"); self.log.see("end")
        if not self.client:
            self.log.insert("end", "(No API key; use Open ChatGPT button.)\n"); return
        q = queue.Queue()
        def worker():
            try:
                resp = self.client.chat.completions.create(
                    model=os.getenv("AUTOBUILD_MODEL","gpt-4o-mini"),
                    messages=[{"role":"system","content":"You assist with code edits and git ops."},
                              {"role":"user","content":text}],
                    temperature=0.2,
                )
                q.put(resp.choices[0].message.content or "")
            except Exception as e:
                q.put(f"[ERROR] {e}")
        threading.Thread(target=worker, daemon=True).start()
        def pump():
            try:
                ans = q.get_nowait(); self.log.insert("end", f"🤖 {ans}\n"); self.log.see("end")
            except queue.Empty:
                self.after(60, pump)
        self.after(60, pump)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        tag = f"{Path(__file__).name} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (TRAELIKE_UI)"
        self.title(f"Autobuild Desktop — {tag}"); self.geometry("1300x820")
        self.projs = dict(projects()); self.active = read_cur()
        if self.active not in self.projs.values(): self.active = next(iter(self.projs.values()))
        write_cur(self.active)
        top = ttk.Frame(self); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Project").pack(side="left")
        self.choice = tk.StringVar(value=next(iter(self.projs.keys())))
        ttk.Combobox(top, textvariable=self.choice, values=list(self.projs.keys()),
                     state="readonly", width=28).pack(side="left", padx=6)
        ttk.Button(top, text="Use", command=self.use_project).pack(side="left")
        ttk.Label(top, text="Active:", padding=(12,0)).pack(side="left")
        self.active_lbl = ttk.Label(top, text=str(self.active), foreground="green"); self.active_lbl.pack(side="left", padx=4)
        ttk.Label(top, text="Commit msg").pack(side="left", padx=(18,4))
        self.commit_msg = ttk.Entry(top, width=40); self.commit_msg.insert(0,"assistant update"); self.commit_msg.pack(side="left")
        ttk.Button(top, text="Commit", command=self.git_commit).pack(side="left", padx=4)
        ttk.Button(top, text="Push", command=lambda: self.run('git push || true')).pack(side="left", padx=4)
        ttk.Button(top, text="Open PR", command=lambda: self.run('gh pr create --fill || gh pr view --web || true')).pack(side="left", padx=4)
        ttk.Label(top, text="API Port").pack(side="left", padx=(18,4))
        self.api_port = ttk.Entry(top, width=8); self.api_port.insert(0,"8080"); self.api_port.pack(side="left")
        ttk.Button(top, text="Start/Stop API", command=self.toggle_api).pack(side="left", padx=6)
        panes = ttk.PanedWindow(self, orient="horizontal"); panes.pack(fill="both", expand=True, padx=8, pady=6)
        left = ttk.Frame(panes, width=260); panes.add(left, weight=1)
        ttk.Label(left, text="Files", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=6, pady=4)
        self.tree = FolderTree(left, on_open=self.on_open_file); self.tree.pack(fill="both", expand=True, padx=6, pady=(0,6))
        center = ttk.Frame(panes); panes.add(center, weight=3)
        self.editor = CodeEditor(center); self.editor.pack(fill="both", expand=True)
        right = ttk.Frame(panes, width=360); panes.add(right, weight=2)
        self.chat = ChatPane(right); self.chat.pack(fill="both", expand=True)
        patch_row = ttk.Frame(self); patch_row.pack(fill="x", padx=8, pady=(0,6))
        ttk.Label(patch_row, text="Patch file").pack(side="left")
        self.patch_entry = ttk.Entry(patch_row, width=60); self.patch_entry.pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(patch_row, text="Browse…", command=self.pick_patch).pack(side="left")
        ttk.Button(patch_row, text="Apply Patch", command=self.apply_patch).pack(side="left", padx=6)
        console = ttk.Frame(self); console.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.out = tk.Text(console, height=12); self.out.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(console, orient="vertical", command=self.out.yview); sb.pack(side="right", fill="y")
        self.out.configure(yscrollcommand=sb.set)
        self.out.insert("end", "Trae-like UI loaded.\n")
        self.tree.populate(self.active)
        self._api_proc = None
    def use_project(self):
        name = self.choice.get(); path = self.projs.get(name)
        if not path or not path.exists(): messagebox.showerror("Path not found", str(path)); return
        self.active = path; write_cur(path); self.active_lbl.configure(text=str(path))
        self.tree.populate(path); self.out.insert("end", f"✔ Active project: {name} → {path}\n"); self.out.see("end")
    def on_open_file(self, p: Path): self.editor.load(p)
    def pick_patch(self):
        p = filedialog.askopenfilename(title="Choose patch", initialdir=str(self.active))
        if p: self.patch_entry.delete(0,"end"); self.patch_entry.insert(0,p)
    def apply_patch(self):
        pf = self.patch_entry.get().strip()
        if not pf: messagebox.showerror("No patch", "Choose a patch file."); return
        msg = self.commit_msg.get().strip() or "assistant update"
        self.run(f'git apply "{pf}" --reject --whitespace=fix && git add -A && git commit -m "{msg}" || true')
    def git_commit(self):
        msg = self.commit_msg.get().strip() or "assistant update"
        self.run(f'git add -A && git commit -m "{msg}" || true')
    def toggle_api(self):
        if getattr(self, "_api_proc", None) and self._api_proc.poll() is None:
            self._api_proc.terminate(); self._api_proc=None
            self.out.insert("end","🛑 API stopped\n"); self.out.see("end"); return
        port = (self.api_port.get().strip() or "8080")
        self._api_proc = subprocess.Popen(["bash","-lc", f'python -m http.server {port}'],
                                          cwd=str(self.active), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        def pump():
            for line in self._api_proc.stdout: self.out.insert("end", line); self.out.see("end")
        threading.Thread(target=pump, daemon=True).start()
        self.out.insert("end", f"🚀 API started at http://localhost:{port}\n"); self.out.see("end")
    def run(self, bash_cmd: str): run_stream(bash_cmd, self.active, self.out)

def main(): App().mainloop()
if __name__ == "__main__": main()
