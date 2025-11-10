from __future__ import annotations
import subprocess, sys, threading
from pathlib import Path
import PySimpleGUI as sg
import yaml

ROOT = Path.cwd()
CONFIG = ROOT / "config" / "autobuild.yml"
CURRENT_FILE = ROOT / ".autobuild_current"

def read_cfg():
    if CONFIG.exists():
        try:
            return yaml.safe_load(CONFIG.read_text()) or {}
        except Exception:
            return {"projects":[]}
    return {"projects":[]}

def write_current(p: Path):
    CURRENT_FILE.write_text(str(p), encoding="utf-8")

def read_current() -> Path:
    if CURRENT_FILE.exists():
        try:
            return Path(CURRENT_FILE.read_text().strip()).expanduser().resolve()
        except Exception:
            pass
    return ROOT

def run_cmd(cmd, cwd=None):
    return subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

def list_projects():
    cfg = read_cfg()
    return [(p.get("name"), Path(p["path"]).expanduser().resolve()) for p in cfg.get("projects",[])]

def gui():
    sg.theme("SystemDefault")
    projects = list_projects()
    names = [n for n,_ in projects] or ["Autobuilder"]

    layout = [
        [sg.Text("Project"), sg.Combo(names, default_value=(names[0] if names else ""), key="-PROJ-", enable_events=True, size=(30,1)),
         sg.Button("Use", key="-USE-"), sg.Text("Active:"), sg.Text("", key="-ACTIVE-", size=(50,1), text_color="green")],
        [sg.HSep()],
        [sg.Frame("Scaffold", [
            [sg.Text("Name"), sg.Input(key="-SC_NAME-", size=(22,1)),
             sg.Text("Out"), sg.Input("./out_cli", key="-SC_OUT-", size=(22,1)),
             sg.Button("Run Scaffold", key="-SCAFFOLD-")]
        ])],
        [sg.Frame("Git Ops", [
            [sg.Text("Patch file"), sg.Input(key="-PATCH-", size=(46,1)), sg.FileBrowse("Browse…"), sg.Button("Apply Patch", key="-PATCH_APPLY-")],
            [sg.Text("Commit message"), sg.Input(key="-CMT-", size=(46,1)), sg.Button("Commit", key="-COMMIT-"),
             sg.Button("Push", key="-PUSH-"), sg.Button("Open PR", key="-PR-")],
            [sg.Button("Status", key="-STATUS-")]
        ])],
        [sg.Frame("API", [
            [sg.Text("Port"), sg.Input("8080", key="-PORT-", size=(8,1)), sg.Button("Start API", key="-API-")]
        ])],
        [sg.HSep()],
        [sg.Text("Output")],
        [sg.Multiline(size=(120,24), key="-LOG-", autoscroll=True, write_only=True, font=("Menlo",10))],
        [sg.Button("Quit")]
    ]
    win = sg.Window("Autobuild Desktop", layout, finalize=True)

    active_path = read_current()
    win["-ACTIVE-"].update(str(active_path))

    def append(msg): win["-LOG-"].print(msg, end="")

    def run_stream(cmd, cwd):
        append(f"> {' '.join(cmd)}   (in {cwd})\n")
        proc = run_cmd(cmd, cwd=cwd)
        for line in proc.stdout:
            append(line)
        proc.wait()
        append(f"\n[exit {proc.returncode}]\n\n")

    while True:
        ev, vals = win.read()
        if ev in (sg.WIN_CLOSED, "Quit"):
            break

        if ev in ("-USE-", "-PROJ-"):
            name = vals["-PROJ-"]
            proj_map = dict(projects)
            if name in proj_map:
                p = proj_map[name]
                if not p.exists():
                    append(f"[ERROR] path not found: {p}\n")
                else:
                    write_current(p)
                    active_path = p
                    win["-ACTIVE-"].update(str(p))
                    append(f"[OK] Active project -> {p}\n")
            else:
                append("[WARN] Unknown project; update config/autobuild.yml\n")

        if ev == "-SCAFFOLD-":
            name = vals["-SC_NAME-"] or "hello_world"
            out = vals["-SC_OUT-"] or "./out_cli"
            cmd = ["autobuilder", "--name", name, "--out", out]
            threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

        if ev == "-PATCH_APPLY-":
            patch = vals["-PATCH-"]
            if not patch:
                append("[WARN] Choose a patch file\n")
            else:
                cmd = [sys.executable, "tools/patcher.py", patch]
                threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

        if ev == "-COMMIT-":
            msg = vals["-CMT-"] or "assistant update"
            cmd = [sys.executable, "tools/autobuild_term.py", "commit", "-m", msg]
            threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

        if ev == "-PUSH-":
            cmd = [sys.executable, "tools/autobuild_term.py", "push"]
            threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

        if ev == "-PR-":
            cmd = [sys.executable, "tools/autobuild_term.py", "pr"]
            threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

        if ev == "-STATUS-":
            cmd = ["git", "status"]
            threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

        if ev == "-API-":
            port = vals["-PORT-"] or "8080"
            helper = active_path / "scripts" / "free-port-8080.sh"
            if helper.exists():
                threading.Thread(target=run_stream, args=([str(helper)], str(active_path)), daemon=True).start()
            cmd = ["uvicorn", "autoappbuilder.api.app:app", "--reload", "--port", str(port)]
            threading.Thread(target=run_stream, args=(cmd, str(active_path)), daemon=True).start()

    win.close()

if __name__ == "__main__":
    gui()
