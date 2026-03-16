import json
from pwbs.api.main import create_app
app = create_app()
spec = app.openapi()
h = spec["paths"].get("/api/v1/admin/health", {}).get("get", {})
print("summary:", repr(h.get("summary")))
print("description:", repr(h.get("description")))