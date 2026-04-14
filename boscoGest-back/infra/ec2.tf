# ──────────────────────────────────────────────
# AMI — Amazon Linux 2023 (latest)
# ──────────────────────────────────────────────

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ──────────────────────────────────────────────
# EC2 Instance
# ──────────────────────────────────────────────

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  user_data = templatefile("${path.module}/user_data.sh", {
    database_url   = "postgresql+psycopg2://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
    secret_key     = var.secret_key
    cors_origins   = var.cors_origins
    docker_image   = var.docker_image
    aws_region     = var.aws_region
    ecr_repository = aws_ecr_repository.backend.repository_url
    s3_bucket_name = aws_s3_bucket.uploads.bucket
  })

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.project_name}-backend"
  }
}

# ──────────────────────────────────────────────
# Elastic IP (static public IP)
# ──────────────────────────────────────────────

resource "aws_eip" "backend" {
  instance = aws_instance.backend.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-backend-eip"
  }
}
