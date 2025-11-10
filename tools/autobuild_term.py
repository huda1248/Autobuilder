from __future__ import annotations
import sys, subprocess, shutil
from pathlib import Path
import typer
from rich import print
import yaml

app = typer.Typer(add_completion=False, help="Autobuild terminal")
CONFIG_FILE = Path("config/autobuild.yml")

def sh(cmd, check=True, cwd=None):
    print(f"[bold]→[/] {' '.join(cmd)}" + (f"  [dim]in {cwd}[/]" if cwd else ""))
    return subprocess.run(cmd, check=check, cwd=cwd)

def load_cfg():
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text()) or {}
    return {"projects": []}

def save_current(path: Path):
    Path(".autobuild_current").write_text(str(path), encoding="utf-8")

def read_current() -> Path:
    f = Path(".autobuild_current")
    return Path(f.read_text().strip()).expanduser().resolve() if f.exists() else Path.cwd()

@app.command("status")
def status():
    sh(["git","status"], check=False, cwd=str(read_current()))

@app.command("patch")
def patch(action: str, path: Path):
    if action != "apply":
        print("[red]Only 'apply' is supported[/]"); raise SystemExit(2)
    if not path.exists():
        print(f"[red]Patch not found:[/] {path}"); raise SystemExit(2)
    cwd = read_current()
    sh([sys.executable,"tools/patcher.py",str(path)], check=False, cwd=str(cwd))
    sh(["git","status"], check=False, cwd=str(cwd))

@app.command("commit")
def commit(message: str = typer.Option(..., "-m")):
    cwd = read_current()
    sh(["git","add","-A"], check=False, cwd=str(cwd))
    sh(["git","commit","-m",message], check=False, cwd=str(cwd))

@app.command("push")
def push(remote: str = "origin", branch: str | None = None):
    cwd = read_current()
    if not branch:
        r = subprocess.run(["git","rev-parse","--abbrev-ref","HEAD"], capture_output=True, text=True, cwd=str(cwd))
        branch = r.stdout.strip() or "main"
    sh(["git","push",remote,branch], check=False, cwd=str(cwd))

@app.command("pr")
def pr(base: str = "main", title: str = "Assistant update", body: str = ""):
    cwd = read_current()
    if shutil.which("gh") is None:
        print("[red]gh CLI not found (brew install gh)[/]"); raise SystemExit(1)
    sh(["gh","pr","create","--fill","--base",base,"--title",title,"--body",body], check=False, cwd=str(cwd))

@app.command("test")
def test():
    cwd = read_current()
    if shutil.which("pytest"): sh(["pytest","-q"], check=False, cwd=str(cwd))
    else: print("[yellow]pytest not found. Skipping.[/]")

@app.command("dev-api")
def dev_api(port: int = 8080):
    cwd = read_current()
    scr = Path("scripts/free-port-8080.sh")
    if scr.exists(): sh([str(scr)], cwd=str(cwd))
    if shutil.which("uvicorn") is None:
        print("[red]uvicorn not installed[/]"); raise SystemExit(1)
    sh(["uvicorn","autoappbuilder.api.app:app","--reload","--port",str(port)], check=False, cwd=str(cwd))

@app.command("scaffold")
def scaffold(name: str, out: str = "./out_cli"):
    cwd = read_current()
    exe = shutil.which("autobuilder")
    if exe is None:
        print("[red]autobuilder CLI not found. pip install -e .[/]"); raise SystemExit(1)
    sh([exe,"--name",name,"--out",out], check=False, cwd=str(cwd))

mpc = typer.Typer(help="Multi-Project Controller")
app.add_typer(mpc, name="mpc")

@mpc.command("list")
def mpc_list():
    cfg = load_cfg()
    cur = (Path(".")/".autobuild_current").read_text().strip() if Path(".autobuild_current").exists() else None
    for p in cfg.get("projects", []):
        path = str(Path(p["path"]).expanduser().resolve())
        mark = "→" if cur and cur == path else " "
        print(f"{mark} {p['name']:20} {path}")

@mpc.command("use")
def mpc_use(name: str):
    cfg = load_cfg()
    for p in cfg.get("projects", []):
        if p["name"] == name:
            path = Path(p["path"]).expanduser().resolve()
            if not path.exists():
                print(f"[red]Path not found:[/] {path}"); raise SystemExit(2)
            save_current(path)
            print(f"[green]Active project:[/] {name} -> {path}")
            return
    print(f"[red]Project not found:[/] {name}")

if __name__ == "__main__":
    app()
