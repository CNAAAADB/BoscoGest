# ──────────────────────────────────────────────
# RDS Subnet Group
# ──────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# ──────────────────────────────────────────────
# RDS PostgreSQL (Free Tier)
# ──────────────────────────────────────────────

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15"

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 0 # Disable autoscaling for free tier

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false
  skip_final_snapshot = true
  storage_encrypted   = false # Free tier doesn't support encryption

  backup_retention_period = 0 # Free tier restriction: no automated backups
  maintenance_window      = "sun:04:00-sun:05:00"

  tags = {
    Name = "${var.project_name}-db"
  }
}
