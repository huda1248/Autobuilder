import subprocess, sys, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml

ROOT = Path.cwd()
CONFIG = ROOT / "config" / "autobuild.yml"
CUR = ROOT / ".autobuild_current"

def cfg():
    try:
        return yaml.safe_load(CONFIG.read_text()) or {}
    except Exception:
        return {"projects":[]}

def projects():
    return [(p.get("name"), Path(p["path"]).expanduser().resolve()) for p in cfg().get("projects",[])]

def write_cur(p: Path): CUR.write_text(str(p), encoding="utf-8")
def read_cur() -> Path:
    try: return Path(CUR.read_text().strip()).expanduser().resolve()
    except Exception: return ROOT

def run_stream(cmd, cwd, out):
    def worker():
        out.insert("end", f"> {' '.join(cmd)}   (in {cwd})\n"); out.see("end")
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout: out.insert("end", line); out.see("end")
        proc.wait(); out.insert("end", f"\n[exit {proc.returncode}]\n\n"); out.see("end")
    threading.Thread(target=worker, daemon=True).start()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Autobuild Desktop")
        self.geometry("980x640")
        self.projs = dict(projects()) or {"Autobuilder": ROOT}
        self.active = read_cur()

        top = ttk.Frame(self); top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Project").pack(side="left")
        self.choice = tk.StringVar(value=next(iter(self.projs.keys())))
        ttk.Combobox(top, textvariable=self.choice, values=list(self.projs.keys()), width=28, state="readonly").pack(side="left", padx=6)
        ttk.Button(top, text="Use", command=self.use_project).pack(side="left")
        ttk.Label(top, text="Active:").pack(side="left", padx=12)
        self.active_lbl = ttk.Label(top, text=str(self.active), foreground="green"); self.active_lbl.pack(side="left", padx=4)

        nb = ttk.Notebook(self); nb.pack(fill="x", padx=8)
        scf = ttk.Frame(nb); nb.add(scf, text="Scaffold")
        ttk.Label(scf, text="Name").grid(row=0, column=0, padx=6, pady=6)
        self.sc_name = ttk.Entry(scf, width=24); self.sc_name.insert(0,"hello_world"); self.sc_name.grid(row=0, column=1)
        ttk.Label(scf, text="Out").grid(row=0, column=2, padx=6)
        self.sc_out = ttk.Entry(scf, width=24); self.sc_out.insert(0,"./out_cli"); self.sc_out.grid(row=0, column=3)
        ttk.Button(scf, text="Run Scaffold", command=self.do_scaffold).grid(row=0, column=4, padx=6)

        gf = ttk.Frame(self); gf.pack(fill="x", padx=8, pady=4)
        ttk.Label(gf, text="Patch file").grid(row=0, column=0, sticky="w")
        self.patch = ttk.Entry(gf, width=60); self.patch.grid(row=0, column=1, padx=6)
        ttk.Button(gf, text="Browse…", command=self.pick_patch).grid(row=0, column=2)
        ttk.Button(gf, text="Apply Patch", command=self.do_patch).grid(row=0, column=3, padx=6)
        ttk.Label(gf, text="Commit msg").grid(row=1, column=0, sticky="w", pady=4)
        self.cmt = ttk.Entry(gf, width=60); self.cmt.insert(0,"assistant update"); self.cmt.grid(row=1, column=1, padx=6)
        ttk.Button(gf, text="Commit", command=self.do_commit).grid(row=1, column=2)
        ttk.Button(gf, text="Push", command=self.do_push).grid(row=1, column=3)
        ttk.Button(gf, text="Open PR", command=self.do_pr).grid(row=1, column=4, padx=6)
        ttk.Button(gf, text="Status", command=self.do_status).grid(row=1, column=5)

        af = ttk.Frame(self); af.pack(fill="x", padx=8, pady=4)
        ttk.Label(af, text="API Port").pack(side="left")
        self.port = ttk.Entry(af, width=8); self.port.insert(0,"8080"); self.port.pack(side="left", padx=6)
        ttk.Button(af, text="Start API", command=self.do_api).pack(side="left")

        self.log = tk.Text(self, height=24, font=("Menlo", 10))
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Button(self, text="Quit", command=self.destroy).pack(pady=(0,8))

    def use_project(self):
        name = self.choice.get()
        p = self.projs.get(name, ROOT)
        if not p.exists():
            messagebox.showerror("Error", f"Path not found: {p}"); return
        self.active = p; write_cur(p); self.active_lbl.config(text=str(p))
        self.log.insert("end", f"[OK] Active project -> {p}\n"); self.log.see("end")

    def pick_patch(self):
        f = filedialog.askopenfilename()
        if f: self.patch.delete(0,"end"); self.patch.insert(0,f)

    def do_scaffold(self):
        name = self.sc_name.get().strip() or "hello_world"
        out = self.sc_out.get().strip() or "./out_cli"
        run_stream(["autobuilder","--name",name,"--out",out], str(self.active), self.log)

    def do_patch(self):
        pf = self.patch.get().strip()
        if not pf: self.log.insert("end","[WARN] choose a patch file\n"); self.log.see("end"); return
        run_stream([sys.executable,"tools/patcher.py",pf], str(self.active), self.log)

    def do_commit(self):
        msg = self.cmt.get().strip() or "assistant update"
        run_stream([sys.executable,"tools/autobuild_term.py","commit","-m",msg], str(self.active), self.log)

    def do_push(self):  run_stream([sys.executable,"tools/autobuild_term.py","push"], str(self.active), self.log)
    def do_pr(self):    run_stream([sys.executable,"tools/autobuild_term.py","pr"],   str(self.active), self.log)
    def do_status(self):run_stream(["git","status"],                                  str(self.active), self.log)
    def do_api(self):
        port = self.port.get().strip() or "8080"
        helper = self.active / "scripts" / "free-port-8080.sh"
        if helper.exists(): run_stream([str(helper)], str(self.active), self.log)
        run_stream(["uvicorn","autoappbuilder.api.app:app","--reload","--port",port], str(self.active), self.log)

if __name__ == "__main__":
    App().mainloop()
