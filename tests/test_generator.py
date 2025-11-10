from pathlib import Path
from autoappbuilder.generator.renderer import TemplateRenderer

def test_scaffold(tmp_path: Path):
    templates_root = Path(__file__).resolve().parents[1] / "autoappbuilder" / "templates"
    r = TemplateRenderer(templates_root)
    out_dir = tmp_path / "out"
    r.scaffold("python_basic", out_dir, {"project_name": "demo", "package_name": "demo"})
    assert (out_dir / "README.md").exists()
