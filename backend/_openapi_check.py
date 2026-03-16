import json
from pwbs.api.main import create_app
app = create_app()
spec = app.openapi()
print("Paths:", len(spec["paths"]))
missing = []
for path, methods in spec["paths"].items():
    for method, details in methods.items():
        if method in ("get","post","put","patch","delete"):
            issues = []
            if not details.get("summary"):
                issues.append("no summary")
            if not details.get("description"):
                issues.append("no description")
            if issues:
                missing.append(method.upper() + " " + path + ": " + ", ".join(issues))
for m in missing:
    print(m)
print("Total issues:", len(missing))
# Also save full spec
with open("_openapi_spec.json", "w") as f:
    json.dump(spec, f, indent=2)
print("Spec saved to _openapi_spec.json")