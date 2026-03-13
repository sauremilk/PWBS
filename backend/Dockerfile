# PWBS Backend  Production Dockerfile
# Multi-stage build for minimal image size

FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install -e ".[llm,vector,graph]"

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system pwbs && adduser --system --ingroup pwbs pwbs

COPY --from=builder /install /usr/local
COPY . .

USER pwbs

EXPOSE 8000

CMD ["uvicorn", "pwbs.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]