"""Generate Postman Collection from OpenAPI and validate schema (TASK-193)."""
import json
import uuid

spec = json.load(open("_openapi_spec.json"))

# Build Postman Collection v2.1
collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "PWBS API",
        "description": spec.get("info", {}).get("description", ""),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [],
    "variable": [
        {"key": "baseUrl", "value": "http://localhost:8000", "type": "string"},
        {"key": "accessToken", "value": "", "type": "string"},
    ],
}

# Group by tag
tag_groups: dict[str, list] = {}
for path, methods in spec["paths"].items():
    for method, details in methods.items():
        if method not in ("get", "post", "put", "patch", "delete"):
            continue
        tags = details.get("tags", ["default"])
        tag = tags[0] if tags else "default"

        # Build request
        url_parts = path.lstrip("/").split("/")
        url_segments = []
        for part in url_parts:
            if part.startswith("{") and part.endswith("}"):
                url_segments.append(":" + part[1:-1])
            else:
                url_segments.append(part)

        request_item = {
            "name": details.get("summary", f"{method.upper()} {path}"),
            "request": {
                "method": method.upper(),
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "Authorization", "value": "Bearer {{accessToken}}"},
                ],
                "url": {
                    "raw": "{{baseUrl}}" + path,
                    "host": ["{{baseUrl}}"],
                    "path": url_segments,
                },
                "description": details.get("description", ""),
            },
            "response": [],
        }

        # Add example request body for POST/PATCH/PUT
        if method in ("post", "patch", "put"):
            rb = details.get("requestBody", {})
            content = rb.get("content", {}).get("application/json", {})
            schema = content.get("schema", {})
            if schema.get(""):
                ref_name = schema[""].split("/")[-1]
                schema_def = spec.get("components", {}).get("schemas", {}).get(ref_name, {})
                example = _build_example(schema_def, spec)
                request_item["request"]["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(example, indent=2),
                    "options": {"raw": {"language": "json"}},
                }

        # Add example response
        for status_code, resp_info in details.get("responses", {}).items():
            resp_content = resp_info.get("content", {}).get("application/json", {})
            resp_schema = resp_content.get("schema", {})
            example = {}
            if resp_schema.get(""):
                ref_name = resp_schema[""].split("/")[-1]
                schema_def = spec.get("components", {}).get("schemas", {}).get(ref_name, {})
                example = _build_example(schema_def, spec)

            request_item["response"].append({
                "name": f"{status_code} {resp_info.get('description', '')}",
                "status": resp_info.get("description", ""),
                "code": int(status_code) if status_code.isdigit() else 0,
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": json.dumps(example, indent=2) if example else "",
            })

        tag_groups.setdefault(tag, []).append(request_item)


def _build_example(schema_def, spec):
    props = schema_def.get("properties", {})
    example = {}
    for prop_name, prop_info in props.items():
        if "" in prop_info:
            ref_name = prop_info[""].split("/")[-1]
            nested = spec.get("components", {}).get("schemas", {}).get(ref_name, {})
            example[prop_name] = _build_example(nested, spec)
        elif prop_info.get("type") == "string":
            example[prop_name] = prop_info.get("example", "string")
        elif prop_info.get("type") == "integer":
            example[prop_name] = prop_info.get("example", 0)
        elif prop_info.get("type") == "number":
            example[prop_name] = prop_info.get("example", 0.0)
        elif prop_info.get("type") == "boolean":
            example[prop_name] = prop_info.get("example", True)
        elif prop_info.get("type") == "array":
            example[prop_name] = []
        elif prop_info.get("type") == "object":
            example[prop_name] = {}
        else:
            example[prop_name] = None
    return example


# Build folder structure
for tag_name, items in sorted(tag_groups.items()):
    collection["item"].append({
        "name": tag_name,
        "item": items,
    })

# Write
import os
os.makedirs("../docs/api", exist_ok=True)
with open("../docs/api/pwbs-collection.json", "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)
print(f"Postman Collection written: {len(spec['paths'])} paths, {sum(len(v) for v in tag_groups.values())} requests")