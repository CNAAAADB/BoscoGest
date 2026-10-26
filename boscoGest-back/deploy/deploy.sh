#!/usr/bin/env bash
#
# Deploy the backend to the EC2 instance behind Caddy/TLS.
#
# Replaces the by-hand sequence in DEPLOY_FEATURES.md (build, push, ssh, edit
# compose, restart). Images are tagged by commit SHA rather than :latest, so a
# rollback is `IMAGE_TAG=<previous-sha> ./deploy.sh` instead of guessing what
# :latest pointed at.
#
# Usage:
#   ./deploy/deploy.sh                 # build, push and deploy HEAD
#   ./deploy/deploy.sh --no-build      # deploy an already-pushed tag
#   IMAGE_TAG=abc1234 ./deploy/deploy.sh --no-build   # roll back to a tag
#
set -euo pipefail

cd "$(dirname "$0")/.."

# ── Configuration ───────────────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-eu-west-1}"
ECR_REPO="${ECR_REPO:-909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/boscogest-key.pem}"
EC2_HOST="${EC2_HOST:-ec2-user@52.51.49.110}"
REMOTE_DIR="/opt/boscogest"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
BUILD=1

[[ "${1:-}" == "--no-build" ]] && BUILD=0

if [[ ! -f "$SSH_KEY" ]]; then
  echo "SSH key not found at $SSH_KEY — set SSH_KEY=..." >&2
  exit 1
fi

if [[ ! -f deploy/.env.prod ]]; then
  cat >&2 <<'MSG'
deploy/.env.prod is missing.

It holds the production environment for the container and is deliberately not
versioned. Copy deploy/.env.prod.example, fill it in, and keep it out of git.
MSG
  exit 1
fi

echo "==> Deploying ${IMAGE_TAG} to ${EC2_HOST}"

# ── Build and push ──────────────────────────────────────────────────────────
if [[ $BUILD -eq 1 ]]; then
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Working tree is dirty. Commit first so the image tag matches the code." >&2
    exit 1
  fi

  echo "==> Logging in to ECR"
  aws ecr get-login-password --region "$AWS_REGION" \
    | docker login --username AWS --password-stdin "${ECR_REPO%%/*}"

  echo "==> Building for linux/amd64 (the instance is x86_64, this host may not be)"
  docker buildx build \
    --platform linux/amd64 \
    -t "${ECR_REPO}:${IMAGE_TAG}" \
    --push \
    .
fi

# ── Ship the deployment files ───────────────────────────────────────────────
echo "==> Copying compose file, Caddyfile and environment"
ssh -i "$SSH_KEY" "$EC2_HOST" "sudo mkdir -p ${REMOTE_DIR} && sudo chown ec2-user:ec2-user ${REMOTE_DIR}"
scp -i "$SSH_KEY" \
  deploy/docker-compose.prod.yml \
  deploy/Caddyfile \
  "${EC2_HOST}:${REMOTE_DIR}/"
scp -i "$SSH_KEY" deploy/.env.prod "${EC2_HOST}:${REMOTE_DIR}/.env"

# ── Restart ─────────────────────────────────────────────────────────────────
echo "==> Pulling and restarting"
ssh -i "$SSH_KEY" "$EC2_HOST" bash -s <<REMOTE
set -euo pipefail
cd ${REMOTE_DIR}

# DOCKER_IMAGE is interpolated by compose from the environment, so the tag is
# explicit rather than baked into the file.
echo "DOCKER_IMAGE=${ECR_REPO}:${IMAGE_TAG}" >> .env

aws ecr get-login-password --region ${AWS_REGION} \
  | sudo docker login --username AWS --password-stdin "${ECR_REPO%%/*}"

sudo docker compose -f docker-compose.prod.yml pull
sudo docker compose -f docker-compose.prod.yml up -d --remove-orphans
sudo docker image prune -f
REMOTE

# ── Verify ──────────────────────────────────────────────────────────────────
echo "==> Waiting for the container to report healthy"
for i in $(seq 1 20); do
  status=$(ssh -i "$SSH_KEY" "$EC2_HOST" \
    "sudo docker inspect -f '{{.State.Health.Status}}' boscogest_back 2>/dev/null || echo starting")
  if [[ "$status" == "healthy" ]]; then
    echo "==> Healthy. Deployed ${IMAGE_TAG}."
    exit 0
  fi
  sleep 5
done

echo "Container did not become healthy. Recent logs:" >&2
ssh -i "$SSH_KEY" "$EC2_HOST" "sudo docker compose -f ${REMOTE_DIR}/docker-compose.prod.yml logs --tail=50 back" >&2
exit 1
