import argparse
from pathlib import Path
from .renderer import TemplateRenderer

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autobuilder",
        description="Scaffold projects from Jinja templates.",
    )
    p.add_argument("--template", "-t", default="python_basic", help="Template name")
    p.add_argument("--out", "-o", default="./out", help="Output directory")
    p.add_argument("--name", "-n", required=True, help="Project/package name (e.g., my_app)")
    return p

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = Path(args.out).resolve()
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    r = TemplateRenderer(templates_root)

    safe = args.name.replace("-", "_").replace(" ", "_")
    context = {"project_name": safe, "package_name": safe}
    r.scaffold(args.template, out_dir, context)
    print(f"✅ Scaffolding complete: {out_dir}")
    return 0
