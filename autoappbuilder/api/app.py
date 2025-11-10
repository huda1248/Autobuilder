from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from ..generator.renderer import TemplateRenderer
from ..utils.store import InMemoryStore

app = FastAPI(title="Autobuilder API", version="0.1.0")
db = InMemoryStore()

class BundleReq(BaseModel):
    name: str
    meta: dict | None = None

class DeployReq(BaseModel):
    bundle_id: str
    target: str

class ScaffoldReq(BaseModel):
    template: str = "python_basic"
    out: str
    name: str

@app.get("/catalog")
def catalog():
    return {"items": db.list_catalog()}

@app.get("/bundles")
def list_bundles():
    return {"items": db.list_bundles()}

@app.post("/bundles")
def create_bundle(req: BundleReq):
    return db.create_bundle(req.name, req.meta)

@app.get("/deployments")
def list_deployments():
    return {"items": db.list_deployments()}

@app.post("/deployments")
def create_deployment(req: DeployReq):
    if req.bundle_id not in {b["id"] for b in db.list_bundles()}:
        raise HTTPException(status_code=404, detail="bundle not found")
    return db.create_deployment(req.bundle_id, req.target)

@app.post("/scaffold")
def scaffold(req: ScaffoldReq):
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    r = TemplateRenderer(templates_root)
    out_dir = Path(req.out).resolve()
    safe = req.name.replace("-", "_").replace(" ", "_")
    context = {"project_name": safe, "package_name": safe}
    r.scaffold(req.template, out_dir, context)
    return {"status": "ok", "out": str(out_dir)}
