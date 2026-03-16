import json
from pwbs.api.main import create_app
app = create_app()
spec = app.openapi()
# Check which endpoints lack description
for path, methods in spec["paths"].items():
    for method, details in methods.items():
        if method in ("get","post","put","patch","delete"):
            if not details.get("description"):
                opid = details.get("operationId", "?")
                print(method.upper(), path, "->", opid)