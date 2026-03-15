"""Generate OpenAPI schema and Postman collection from FastAPI app (TASK-193).

Usage:
    python scripts/export_openapi.py
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "dev-only-placeholder-key-32chars!")
os.environ.setdefault("ENCRYPTION_MASTER_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMg==")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("DEBUG", "1")

from pwbs.api.main import create_app  # noqa: E402

DOCS_API = Path(__file__).resolve().parent.parent.parent / "docs" / "api"


def main() -> None:
    app = create_app()
    schema = app.openapi()
    DOCS_API.mkdir(parents=True, exist_ok=True)

    openapi_path = DOCS_API / "openapi.json"
    openapi_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"OpenAPI schema -> {openapi_path}")

    paths = schema.get("paths", {})
    tag_groups: dict[str, list[dict]] = {}

    for path, methods in sorted(paths.items()):
        for method, op in methods.items():
            tag = (op.get("tags") or ["Ungrouped"])[0]
            summary = op.get("summary", f"{method.upper()} {path}")
            desc = op.get("description", "")
            url_parts = path.strip("/").split("/")
            path_vars = [
                {"key": p[1:-1], "value": "", "description": p[1:-1]}
                for p in url_parts if p.startswith("{") and p.endswith("}")
            ]
            headers = [{"key": "Authorization", "value": "Bearer {{accessToken}}", "type": "text"}]
            if method.upper() in ("POST", "PUT", "PATCH"):
                headers.append({"key": "Content-Type", "value": "application/json", "type": "text"})
            item: dict = {
                "name": summary,
                "request": {
                    "method": method.upper(),
                    "header": headers,
                    "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": url_parts, "variable": path_vars},
                    "description": desc,
                },
                "response": [],
            }
            tag_groups.setdefault(tag, []).append(item)

    collection = {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": "PWBS API",
            "description": schema.get("info", {}).get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000", "type": "string"},
            {"key": "accessToken", "value": "", "type": "string"},
        ],
        "item": [{"name": t, "item": tag_groups[t]} for t in sorted(tag_groups)],
    }

    postman_path = DOCS_API / "pwbs-collection.json"
    postman_path.write_text(
        json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    total = sum(len(v) for v in tag_groups.values())
    print(f"Postman collection -> {postman_path}  ({total} requests in {len(tag_groups)} folders)")


if __name__ == "__main__":
    main()
