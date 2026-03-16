import json
from pwbs.api.main import create_app
app = create_app()
spec = app.openapi()
wh = spec["paths"].get("/api/v1/webhook-subscriptions", {})
for method, details in wh.items():
    print("METHOD:", method)
    print("summary:", details.get("summary"))
    print("description:", details.get("description"))
    print()