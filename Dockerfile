FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e ".[all]"

ENV GTP_IBKR_USE_STUB=1
ENV GTP_PAPER_FIRST=true
ENV GTP_AUDIT_DB_PATH=/app/var/audit.sqlite3

RUN mkdir -p /app/var

CMD ["python", "-m", "fincept_terminal"]
