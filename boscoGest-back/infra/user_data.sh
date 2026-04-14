#!/bin/bash
set -euo pipefail

# Log everything
exec > >(tee /var/log/user_data.log) 2>&1
echo "=== BoscoGest EC2 bootstrap started at $(date) ==="

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl enable docker
systemctl start docker

# Install Docker Compose v2
DOCKER_COMPOSE_VERSION="v2.24.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Install Git
yum install -y git

# Create app directory
mkdir -p /opt/boscogest
cd /opt/boscogest

# Login to ECR (AWS CLI is pre-installed on Amazon Linux 2023)
ECR_REGISTRY=$(echo "${ecr_repository}" | cut -d'/' -f1)
aws ecr get-login-password --region ${aws_region} | \
  docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Write environment file — values injected by Terraform templatefile()
cat > .env <<'ENVEOF'
DATABASE_URL=${database_url}
SECRET_KEY=${secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=${cors_origins}
STORAGE_BACKEND=s3
S3_BUCKET_NAME=${s3_bucket_name}
AWS_REGION=${aws_region}
ENVEOF

# Write docker-compose for production (no local DB — uses RDS, no local uploads — uses S3)
cat > docker-compose.yml <<'COMPOSEEOF'
services:
  back:
    image: ${docker_image}
    container_name: boscogest_back
    restart: always
    env_file:
      - .env
    ports:
      - "8000:8000"
COMPOSEEOF

# Pull and start
docker compose pull
docker compose up -d

echo "=== BoscoGest EC2 bootstrap completed at $(date) ==="
