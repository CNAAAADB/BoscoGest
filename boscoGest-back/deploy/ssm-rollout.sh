#!/usr/bin/env bash
# Executed by AWS Systems Manager as root on the BoscoGest EC2 host.
# Do not print .env: it contains production credentials.
set -euo pipefail
umask 077

cd /opt/boscogest
test -f .env
test -f docker-compose.prod.yml
test -n "${NEW_IMAGE:-}"

OLD_IMAGE="$(sed -n 's/^DOCKER_IMAGE=//p' .env | tail -n 1)"
if [[ -z "${OLD_IMAGE}" ]]; then
  echo "No previous DOCKER_IMAGE configured; refusing an unsafe rollout." >&2
  exit 1
fi

set_image() {
  local image="$1"
  sed -i '/^DOCKER_IMAGE=/d' .env
  printf 'DOCKER_IMAGE=%s\n' "$image" >> .env
}

rollback() {
  echo "Backend did not become healthy; restoring the previous image." >&2
  set_image "$OLD_IMAGE"
  docker compose -f docker-compose.prod.yml up -d --no-deps back || true
}
trap rollback ERR

REGISTRY="${NEW_IMAGE%%/*}"
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin "$REGISTRY"
docker pull "$NEW_IMAGE"

set_image "$NEW_IMAGE"
# Keep Caddy running: do not compose down and do not recreate its certificates.
docker compose -f docker-compose.prod.yml up -d --no-deps back

healthy=0
for i in $(seq 1 36); do
  state="$(docker inspect -f '{{.State.Health.Status}}' boscogest_back 2>/dev/null || echo starting)"
  if [[ "$state" == "healthy" ]]; then
    healthy=1
    break
  fi
  if [[ "$state" == "unhealthy" && "$i" -gt 12 ]]; then
    break
  fi
  sleep 5
done

if [[ "$healthy" != "1" ]]; then
  echo "New container failed its health check." >&2
  exit 1
fi
trap - ERR
echo "BoscoGest backend healthy; release image: $NEW_IMAGE"
