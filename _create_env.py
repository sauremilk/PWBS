"""Generate .env file with secure random secrets for local development."""

import secrets
from pathlib import Path

jwt_secret = secrets.token_urlsafe(64)
encryption_key = secrets.token_urlsafe(32)

env_content = f"""# PWBS .env – Lokale Entwicklung (generiert)
# NIEMALS committen!

# Allgemein
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://pwbs:pwbs_dev@localhost:5432/pwbs

# Weaviate
WEAVIATE_URL=http://localhost:8080

# Neo4j (optional, nur mit --profile graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=dev_password

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM – Lokales Ollama (kostenlos, kein API-Key noetig)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# JWT Auth (HS256 fuer lokale Entwicklung)
JWT_SECRET_KEY={jwt_secret}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_PRIVATE_KEY=
JWT_PUBLIC_KEY=

# Verschluesselung
ENCRYPTION_MASTER_KEY={encryption_key}

# OAuth2 (leer fuer lokale Entwicklung)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=

# Email (lokal nicht noetig)
EMAIL_PROVIDER=smtp
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM_ADDRESS=noreply@pwbs.app
EMAIL_FROM_NAME=PWBS
"""

env_path = Path("c:/Users/mickg/PWBS/.env")
if env_path.exists():
    print("SKIP: .env existiert bereits")
else:
    env_path.write_text(env_content, encoding="utf-8")
    print(f"OK: .env erstellt mit Ollama (qwen2.5:14b) als LLM-Provider")
    print(f"JWT_SECRET_KEY={jwt_secret[:12]}...")
    print(f"ENCRYPTION_MASTER_KEY={encryption_key[:12]}...")
