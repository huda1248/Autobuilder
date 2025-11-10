#!/usr/bin/env python3
from __future__ import annotations
import sys, os, json, subprocess, shutil
from pathlib import Path
import traceback

# This is a minimal JSON-RPC 2.0 over stdio server. Each request is a single JSON line.
# Methods exposed mirror Autobuild Terminal functionality.

ROOT = Path.cwd()
CURRENT = ROOT / ".autobuild_current"  # selected project path written by CLI/UI

def log(*a):
    print("[mcp]", *a, file=sys.stderr)

def read_current() -> Path:
    if CURRENT.exists():
        try:
            return Path(CURRENT.read_text().strip()).expanduser().resolve()
        except Exception:
            pass
    return ROOT

def run(cmd, cwd=None):
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate()
    return p.returncode, out

def ok(result):
    return {"jsonrpc":"2.0","result":result}

def err(code, message, data=None):
    e = {"code":code,"message":message}
    if data is not None:
        e["data"]=data
    return {"jsonrpc":"2.0","error":e}

def method_list(_params):
    return ok({
        "tools":[
            "tools.applyPatch","tools.commit","tools.push","tools.openPR",
            "tools.scaffold","tools.devApi","mpc.list","mpc.use","git.status"
        ]
    })

def tools_apply_patch(params):
    path = params.get("patchPath")
    if not path: return err(-32602, "patchPath required")
    cwd = read_current()
    # prefer git apply
    rc, out = run(["git","apply","--whitespace=fix", path], cwd=str(cwd))
    if rc != 0:
        rc, out2 = run(["patch","-p0","-N","-r","patch.rej","-i", path], cwd=str(cwd))
        out += "\n[FALLBACK patch(1)]\n" + out2
        if rc != 0:
            return err(1, "apply failed", {"stdout": out})
    return ok({"stdout": out, "cwd": str(cwd)})

def tools_commit(params):
    msg = params.get("message") or "assistant update"
    cwd = read_current()
    run(["git","add","-A"], cwd=str(cwd))
    rc, out = run(["git","commit","-m", msg], cwd=str(cwd))
    return ok({"stdout": out, "cwd": str(cwd), "rc": rc})

def tools_push(params):
    remote = params.get("remote","origin")
    branch = params.get("branch")
    cwd = read_current()
    if not branch:
        rc, out = run(["git","rev-parse","--abbrev-ref","HEAD"], cwd=str(cwd))
        branch = out.strip() or "main"
    rc, out = run(["git","push", remote, branch], cwd=str(cwd))
    return ok({"stdout": out, "cwd": str(cwd), "rc": rc})

def tools_open_pr(params):
    base = params.get("base","main")
    title = params.get("title","Assistant update")
    body = params.get("body","")
    cwd = read_current()
    if shutil.which("gh") is None:
        return err(2,"gh CLI not found")
    rc, out = run(["gh","pr","create","--fill","--base",base,"--title",title,"--body",body], cwd=str(cwd))
    return ok({"stdout": out, "cwd": str(cwd), "rc": rc})

def tools_scaffold(params):
    name = params.get("name")
    outdir = params.get("out","./out_cli")
    if not name: return err(-32602,"name required")
    if shutil.which("autobuilder") is None:
        return err(3,"autobuilder CLI not found")
    cwd = read_current()
    rc, out = run(["autobuilder","--name",name,"--out",outdir], cwd=str(cwd))
    return ok({"stdout": out, "cwd": str(cwd), "rc": rc})

def tools_dev_api(params):
    port = str(params.get("port", 8080))
    cwd = read_current()
    # free the port first if script exists
    script = Path(cwd) / "scripts" / "free-port-8080.sh"
    if script.exists():
        run([str(script)], cwd=str(cwd))
    if shutil.which("uvicorn") is None:
        return err(4,"uvicorn not found")
    # start uvicorn (non-blocking) and return immediately
    subprocess.Popen(["uvicorn","autoappbuilder.api.app:app","--reload","--port",port], cwd=str(cwd))
    return ok({"message": f"Started API on {port}", "cwd": str(cwd)})

def mpc_list(_params):
    cfg = (ROOT / "config" / "autobuild.yml")
    if not cfg.exists():
        return ok({"projects":[]})
    try:
        import yaml
        data = yaml.safe_load(cfg.read_text()) or {}
    except Exception as e:
        return err(5,"invalid YAML",{"detail":str(e)})
    return ok({"projects": data.get("projects",[])})

def mpc_use(params):
    name = params.get("name")
    if not name: return err(-32602,"name required")
    cfg = (ROOT / "config" / "autobuild.yml")
    if not cfg.exists():
        return err(6,"config/autobuild.yml not found")
    import yaml
    data = yaml.safe_load(cfg.read_text()) or {}
    for p in data.get("projects", []):
        if p.get("name")==name:
            path = Path(p["path"]).expanduser().resolve()
            if not path.exists():
                return err(7,"path not found",{"path":str(path)})
            CURRENT.write_text(str(path), encoding="utf-8")
            return ok({"active": name, "path": str(path)})
    return err(8,"project not found",{"name":name})

def git_status(_params):
    cwd = read_current()
    rc, out = run(["git","status"], cwd=str(cwd))
    return ok({"stdout": out, "cwd": str(cwd), "rc": rc})

METHODS = {
    "mcp/listTools": method_list,
    "tools.applyPatch": tools_apply_patch,
    "tools.commit": tools_commit,
    "tools.push": tools_push,
    "tools.openPR": tools_open_pr,
    "tools.scaffold": tools_scaffold,
    "tools.devApi": tools_dev_api,
    "mpc.list": mpc_list,
    "mpc.use": mpc_use,
    "git.status": git_status,
}

def handle(line: str):
    try:
        req = json.loads(line)
        method = req.get("method")
        _id = req.get("id")
        params = req.get("params") or {}
        if method not in METHODS:
            resp = {"jsonrpc":"2.0","id":_id,"error":{"code":-32601,"message":"Method not found"}}
        else:
            res = METHODS[method](params)
            res["id"] = _id
            resp = res
    except Exception as e:
        resp = {"jsonrpc":"2.0","error":{"code":-32603,"message":"Internal error","data":traceback.format_exc()}}
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

def main():
    log("MCP server started; waiting for JSON-RPC lines on stdin")
    for line in sys.stdin:
        line = line.strip()
        if not line: 
            continue
        handle(line)

if __name__ == "__main__":
    main()
