from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, StrictUndefined

class TemplateRenderer:
    def __init__(self, templates_root: Path) -> None:
        self.templates_root = templates_root
        self.env = Environment(
            loader=FileSystemLoader(str(templates_root)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            autoescape=False,
        )

    def scaffold(self, template_name: str, out_dir: Path, context: Dict[str, Any]) -> None:
        src_root = self.templates_root / template_name
        if not src_root.is_dir():
            raise FileNotFoundError(f"Template '{template_name}' not found at {src_root}")

        for src_path in src_root.rglob("*"):
            rel = src_path.relative_to(src_root)

            rendered_parts = []
            for part in rel.parts:
                tpl = self.env.from_string(part)
                rendered_parts.append(tpl.render(**context))
            rendered_rel = Path(*rendered_parts)
            dst_path = out_dir / rendered_rel

            if src_path.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
                continue

            template = self.env.get_template(str(Path(template_name) / rel))
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            dst_path.write_text(template.render(**context), encoding="utf-8")
