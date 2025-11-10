from typing import Dict, Any, List
from uuid import uuid4

class InMemoryStore:
    def __init__(self):
        self.catalog: List[Dict[str, Any]] = [
            {"id": "tmpl-python-basic", "name": "Python Basic", "kind": "template"},
        ]
        self.bundles: Dict[str, Dict[str, Any]] = {}
        self.deployments: Dict[str, Dict[str, Any]] = {}

    def list_catalog(self):
        return self.catalog

    def create_bundle(self, name: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
        bid = str(uuid4())
        bundle = {"id": bid, "name": name, "meta": meta or {}}
        self.bundles[bid] = bundle
        return bundle

    def list_bundles(self):
        return list(self.bundles.values())

    def create_deployment(self, bundle_id: str, target: str) -> Dict[str, Any]:
        did = str(uuid4())
        dep = {"id": did, "bundle_id": bundle_id, "target": target, "status": "created"}
        self.deployments[did] = dep
        return dep

    def list_deployments(self):
        return list(self.deployments.values())
