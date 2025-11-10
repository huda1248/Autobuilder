# Autobuilder — MVP Plus

This is a runnable, minimal implementation aligned to your architecture:

- **API (FastAPI):** endpoints for `/bundles`, `/catalog`, `/deployments`, `/uploads` (in-memory store).
- **Admin (FastAPI + Jinja):** lightweight HTML pages served from `admin/templates` with simple JS.
- **Generator:** Jinja-based renderer that scaffolds projects from templates.
- **Automation templates:** GitHub Actions CI, Kubernetes Deployment, Slack webhook.
- **Tests:** basic API and generator tests.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn autoappbuilder.api.app:app --reload --port 8080
# Try endpoints:
curl -s http://127.0.0.1:8080/catalog
curl -s -X POST http://127.0.0.1:8080/bundles -H "Content-Type: application/json" -d '{"name":"demo"}'
```
