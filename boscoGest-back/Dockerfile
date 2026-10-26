# Build stage: install the dependencies into their own prefix so the runtime
# image can take them without the tooling that produced them.
FROM python:3.11.13-slim AS builder

WORKDIR /app

COPY requirements.txt .
# requirements.txt pins psycopg2-binary, which ships wheels, so nothing needs
# compiling. The previous image installed gcc and libpq-dev to build a
# dependency it never built, and kept the compiler in the shipped image.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage.
FROM python:3.11.13-slim

# postgresql-client provides pg_isready, which start.sh waits on. Nothing else
# from the build stage comes across.
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    # A compromise in the application should not be root inside the container.
    && useradd --system --create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --chown=app:app app/ ./app
COPY --chown=app:app alembic/ ./alembic
COPY --chown=app:app alembic.ini .
COPY --chown=app:app start.sh ./start.sh
RUN chmod +x ./start.sh \
    # main.py creates this on startup when STORAGE_BACKEND=local. WORKDIR
    # belongs to root, so the unprivileged user could not, and the container
    # exited with PermissionError before serving a single request.
    && mkdir -p /app/uploads/activities \
    && chown -R app:app /app/uploads

USER app

EXPOSE 8000

# `restart: always` restarts a container that exits; it cannot see one that is
# up but no longer serving. /healthz touches the database, so this notices a
# connection that has gone stale.
#
# Exec form and a timeout of its own, shorter than Docker's. The previous
# `curl … || exit 1` ran through /bin/sh: when /healthz took longer than 10s,
# Docker killed the shell and left curl orphaned, and uvicorn — PID 1 — never
# reaps orphans. In three weeks production gathered 1,057 zombie curls, could
# no longer fork, and every check failed with "Cannot fork". Here the check is
# a single process that gives up by itself at 5s. The compose files also set
# `init: true`, so anything else that ends up orphaned is reaped too.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz', timeout=5).status == 200 else 1)"]

CMD ["./start.sh"]
