#!/bin/bash
set -e

# The host and port are parsed with Python rather than sed: the previous regex
# broke on a password containing '@', on a URL with query parameters, and on an
# omitted port — and a failed parse left DB_HOST empty, so pg_isready looped
# forever instead of reporting anything.
read -r DB_HOST DB_PORT <<< "$(python -c '
import os
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
# urlparse does not understand the "+driver" suffix SQLAlchemy uses.
parsed = urlparse(url.replace("postgresql+psycopg2://", "postgresql://"))
print(parsed.hostname or "", parsed.port or 5432)
')"

if [ -z "$DB_HOST" ]; then
  echo "Could not determine the database host from DATABASE_URL." >&2
  exit 1
fi

echo "Waiting for database at $DB_HOST:$DB_PORT..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
  sleep 1
done
echo "Database is ready."

echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
