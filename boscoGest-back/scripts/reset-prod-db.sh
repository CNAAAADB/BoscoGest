#!/usr/bin/env bash
#
# Wipe the production database and rebuild it from migrations.
#
# This is destructive and irreversible. It takes an RDS snapshot first and
# waits for it to complete, so there is always a way back, but restoring one
# takes ~10 minutes and creates a new instance with a new endpoint.
#
# The rebuild goes through Alembic rather than a schema dump, which is what
# makes it reproducible: the same command produces the same schema on an empty
# database anywhere.
#
# Usage:
#   ./scripts/reset-prod-db.sh                 # snapshot, wipe, migrate, seed
#   ./scripts/reset-prod-db.sh --with-salesian # also load the entity hierarchy
#   ./scripts/reset-prod-db.sh --dry-run       # show what would happen
#   ./scripts/reset-prod-db.sh --skip-snapshot # only when the data is already worthless
#
# Requires: psql, ssh, aws cli, and the backend virtualenv for Alembic.
#
set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────
SSH_KEY="${SSH_KEY:-$HOME/.ssh/boscogest-key.pem}"
EC2_HOST="${EC2_HOST:-ec2-user@52.51.49.110}"
RDS_ENDPOINT="${RDS_ENDPOINT:-boscogest-db.cjiy24qmwbpu.eu-west-1.rds.amazonaws.com}"
RDS_INSTANCE_ID="${RDS_INSTANCE_ID:-boscogest-db}"
RDS_PORT=5432
DB_NAME="${DB_NAME:-boscogest}"
DB_USER="${DB_USER:-boscogest_admin}"
LOCAL_PORT="${LOCAL_PORT:-5433}"
AWS_REGION="${AWS_REGION:-eu-west-1}"

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${BACKEND_DIR}/.venv"
SALESIAN_SQL="${BACKEND_DIR}/scripts/seed_salesian_entities.sql"

WITH_SALESIAN=0
DRY_RUN=0
SKIP_SNAPSHOT=0
NO_TUNNEL=0

for arg in "$@"; do
  case "$arg" in
    --with-salesian) WITH_SALESIAN=1 ;;
    --dry-run)       DRY_RUN=1 ;;
    --skip-snapshot) SKIP_SNAPSHOT=1 ;;
    # Talk to LOCAL_PORT directly instead of opening a tunnel. Use it when a
    # tunnel is already open (db-prod.sh --tunnel), or to rehearse the whole
    # run against a throwaway local database before touching production.
    --no-tunnel)     NO_TUNNEL=1; SKIP_SNAPSHOT=1 ;;
    -h|--help)       sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

# ── Preflight ───────────────────────────────────────────────────────────────
bold "==> Checking prerequisites"

# Homebrew's libpq is keg-only, so psql is installed but not on PATH. Find it
# rather than making the caller remember to export it.
PSQL_BIN="${PSQL_BIN:-$(command -v psql || true)}"
if [[ -z "$PSQL_BIN" ]]; then
  for candidate in \
    "$(brew --prefix libpq 2>/dev/null)/bin/psql" \
    /opt/homebrew/opt/libpq/bin/psql \
    /usr/local/opt/libpq/bin/psql
  do
    [[ -x "$candidate" ]] && { PSQL_BIN="$candidate"; break; }
  done
fi
[[ -x "$PSQL_BIN" ]] || {
  red "psql not found."
  echo "Install it (brew install libpq) or set PSQL_BIN=/path/to/psql" >&2
  exit 1
}
echo "  psql: $PSQL_BIN"

REQUIRED_CMDS=(nc)
[[ $NO_TUNNEL -eq 0 ]] && REQUIRED_CMDS+=(ssh aws)
for cmd in "${REQUIRED_CMDS[@]}"; do
  command -v "$cmd" >/dev/null || { red "Missing required command: $cmd"; exit 1; }
done

if [[ $NO_TUNNEL -eq 0 && ! -f "$SSH_KEY" ]]; then
  red "SSH key not found at $SSH_KEY — set SSH_KEY=..."; exit 1
fi
[[ -d "$VENV" ]]    || { red "Backend virtualenv not found at $VENV"; exit 1; }
[[ -f "$BACKEND_DIR/alembic.ini" ]] || { red "alembic.ini not found in $BACKEND_DIR"; exit 1; }

if [[ $WITH_SALESIAN -eq 1 && ! -f "$SALESIAN_SQL" ]]; then
  red "Salesian seed not found at $SALESIAN_SQL"; exit 1
fi

# The seeder refuses to run without this, on purpose: a well-known bootstrap
# password on an internet-facing deployment is a back door.
if [[ -z "${SEED_SUPERADMIN_PASSWORD:-}" ]]; then
  red "SEED_SUPERADMIN_PASSWORD is not set."
  echo "Generate one and re-run, for example:" >&2
  echo '  export SEED_SUPERADMIN_PASSWORD="$(python3 -c "import secrets;print(secrets.token_urlsafe(16))")"' >&2
  exit 1
fi

if [[ -z "${PGPASSWORD:-}" ]]; then
  read -rsp "Password for ${DB_USER}: " PGPASSWORD
  echo
  export PGPASSWORD
fi

# app/config.py validates its inputs at import time, so Alembic cannot even
# load the models without them. Real values come from the production env file
# when it is present; otherwise throwaway ones are enough, since migrations
# neither sign tokens nor serve requests.
if [[ -f "${BACKEND_DIR}/deploy/.env.prod" ]]; then
  set -a; # shellcheck disable=SC1091
  source "${BACKEND_DIR}/deploy/.env.prod"; set +a
  echo "  loaded settings from deploy/.env.prod"
else
  export SECRET_KEY="${SECRET_KEY:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')}"
  export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost}"
  echo "  deploy/.env.prod not found — using throwaway settings for the migration run"
fi

# ── Confirmation ────────────────────────────────────────────────────────────
echo
red   "########################################################"
red   "#  This DESTROYS every row in the production database.  #"
red   "########################################################"
echo
echo "  Instance : ${RDS_INSTANCE_ID} (${RDS_ENDPOINT})"
echo "  Database : ${DB_NAME}"
echo "  Snapshot : $([[ $SKIP_SNAPSHOT -eq 1 ]] && echo 'SKIPPED — no way back' || echo 'yes, taken and awaited first')"
echo "  Salesian : $([[ $WITH_SALESIAN -eq 1 ]] && echo 'yes' || echo 'no')"
echo

if [[ $DRY_RUN -eq 1 ]]; then
  green "Dry run — stopping here."
  exit 0
fi

read -rp "Type the database name (${DB_NAME}) to confirm: " confirm
[[ "$confirm" == "$DB_NAME" ]] || { red "Aborted."; exit 1; }

# ── Snapshot ────────────────────────────────────────────────────────────────
if [[ $SKIP_SNAPSHOT -eq 0 ]]; then
  SNAPSHOT_ID="${RDS_INSTANCE_ID}-prereset-$(date -u +%Y%m%d-%H%M%S)"
  bold "==> Taking snapshot ${SNAPSHOT_ID}"
  aws rds create-db-snapshot \
    --region "$AWS_REGION" \
    --db-instance-identifier "$RDS_INSTANCE_ID" \
    --db-snapshot-identifier "$SNAPSHOT_ID" \
    --query 'DBSnapshot.Status' --output text

  echo "  waiting for it to become available (this usually takes a few minutes)…"
  aws rds wait db-snapshot-completed \
    --region "$AWS_REGION" \
    --db-snapshot-identifier "$SNAPSHOT_ID"
  green "  snapshot ready: ${SNAPSHOT_ID}"
  echo "  restore with: aws rds restore-db-instance-from-db-snapshot \\"
  echo "                  --db-snapshot-identifier ${SNAPSHOT_ID} \\"
  echo "                  --db-instance-identifier ${RDS_INSTANCE_ID}-restored"
fi

# ── Tunnel ──────────────────────────────────────────────────────────────────
TUNNEL_PID=""
cleanup() {
  [[ -n "$TUNNEL_PID" ]] && kill "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT

if [[ $NO_TUNNEL -eq 1 ]]; then
  bold "==> Using localhost:${LOCAL_PORT} directly (no tunnel)"
  nc -z localhost "$LOCAL_PORT" 2>/dev/null || { red "Nothing is listening on localhost:${LOCAL_PORT}."; exit 1; }
else
  # RDS sits in a private subnet, so everything goes through the EC2 bastion.
  bold "==> Opening SSH tunnel localhost:${LOCAL_PORT} -> ${RDS_ENDPOINT}:${RDS_PORT}"

  ssh -i "$SSH_KEY" -N -o ExitOnForwardFailure=yes \
      -L "${LOCAL_PORT}:${RDS_ENDPOINT}:${RDS_PORT}" "$EC2_HOST" &
  TUNNEL_PID=$!

  for _ in $(seq 1 30); do
    nc -z localhost "$LOCAL_PORT" 2>/dev/null && break
    sleep 0.5
  done
  nc -z localhost "$LOCAL_PORT" 2>/dev/null || { red "Tunnel failed to come up."; exit 1; }
  green "  tunnel up"
fi

PSQL=("$PSQL_BIN" -h localhost -p "$LOCAL_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q)

echo "  rows currently in the database:"
"${PSQL[@]}" -tAc "
  SELECT '    users: ' || (SELECT count(*) FROM users)
      || ', entities: ' || (SELECT count(*) FROM entities)
      || ', memberships: ' || (SELECT count(*) FROM memberships)
" 2>/dev/null || echo "    (no schema yet)"

# ── Wipe ────────────────────────────────────────────────────────────────────
bold "==> Dropping the public schema"
# Dropping and recreating the schema removes tables, sequences, native enum
# types and the alembic_version marker in one statement, which is what lets
# the migrations run from scratch rather than from an unknown state.
"${PSQL[@]}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
"${PSQL[@]}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER}; GRANT ALL ON SCHEMA public TO public;"
green "  schema dropped and recreated"

# ── Migrate ─────────────────────────────────────────────────────────────────
bold "==> Applying migrations"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
  export DATABASE_URL="postgresql+psycopg2://${DB_USER}:${PGPASSWORD}@localhost:${LOCAL_PORT}/${DB_NAME}"
  alembic upgrade head
)
green "  migrations applied"

# ── Seed ────────────────────────────────────────────────────────────────────
bold "==> Seeding roles, permissions, the level-1 entity and the superadmin"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
  export DATABASE_URL="postgresql+psycopg2://${DB_USER}:${PGPASSWORD}@localhost:${LOCAL_PORT}/${DB_NAME}"
  python -m app.database.seeds.initial_seeder
)

if [[ $WITH_SALESIAN -eq 1 ]]; then
  bold "==> Loading the Salesian entity hierarchy"
  "${PSQL[@]}" -f "$SALESIAN_SQL"
fi

# ── Verify ──────────────────────────────────────────────────────────────────
bold "==> Verifying"
"${PSQL[@]}" -tAc "
  SELECT '  tables: ' || (SELECT count(*) FROM pg_tables WHERE schemaname='public')
      || E'\n  permissions: ' || (SELECT count(*) FROM permissions)
      || E'\n  roles: ' || (SELECT count(*) FROM roles)
      || E'\n  entities: ' || (SELECT count(*) FROM entities)
      || E'\n  users: ' || (SELECT count(*) FROM users)
      || E'\n  alembic revision: ' || (SELECT version_num FROM alembic_version)
"

if ! "${PSQL[@]}" -tAc "SELECT 1 FROM users WHERE email='superadmin@boscogest.com'" | grep -q 1; then
  red "Superadmin was not created — the seed did not complete."
  exit 1
fi

echo
green "Done. The database was rebuilt from migrations."
echo
bold "Next:"
echo "  1. Log in as superadmin@boscogest.com with the password you set."
echo "     It is flagged must_change_password, so the first login forces a change."
echo "  2. Rotate SECRET_KEY in deploy/.env.prod and redeploy. Every token issued"
echo "     against the old database is now meaningless anyway, so this is the"
echo "     cheapest moment to do it."
echo "  3. Create a user and confirm the welcome email arrives."
