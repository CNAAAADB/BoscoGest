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

# Optional slow-query diagnostics. Disabled by default to avoid changing
# production RDS until a maintenance window has been selected.
resource "aws_db_parameter_group" "slow_queries" {
  count  = var.db_enable_slow_query_logging ? 1 : 0
  name   = "${var.project_name}-postgres15-slow-queries"
  family = "postgres15"

  parameter {
    name         = "log_min_duration_statement"
    value        = "500"
    apply_method = "immediate"
  }

  # Prepared-statement bind values can contain member data and search terms.
  parameter {
    name         = "log_parameter_max_length"
    value        = "0"
    apply_method = "immediate"
  }

  tags = { Name = "${var.project_name}-postgres15-slow-queries" }
}

# ──────────────────────────────────────────────
# RDS PostgreSQL (Free Tier)
# ──────────────────────────────────────────────

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15"

  # Restores the instance from this snapshot on creation. It must be cleared
  # before any apply that replaces the instance, or the old data comes straight
  # back — which would silently undo a database reset.
  snapshot_identifier = var.restore_from_snapshot == "" ? null : var.restore_from_snapshot

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 0 # Disable autoscaling for free tier

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false

  # Changing the parameter group of a live RDS instance may require a reboot.
  # Apply this only during a planned maintenance window.
  parameter_group_name = var.db_enable_slow_query_logging ? aws_db_parameter_group.slow_queries[0].name : null

  # Always keep a snapshot when the instance is destroyed. Combined with
  # deletion_protection, this makes an accidental `terraform destroy` recoverable.
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project_name}-db-final-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  deletion_protection       = var.db_deletion_protection

  # The previous comment claimed the free tier does not support encryption.
  # That is not correct: db.t3.micro encrypts at rest with an AWS-managed KMS
  # key at no extra cost. It does, however, require replacing the instance —
  # encryption cannot be turned on in place — so the moment to do it is while
  # the data is disposable.
  storage_encrypted = var.db_storage_encrypted

  # Likewise, automated backups are not a paid feature; retention is free up to
  # the size of the allocated storage. Zero meant no point-in-time recovery at
  # all, so any corruption or accidental delete was unrecoverable.
  backup_retention_period = var.db_backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Without this, RDS queues changes until the maintenance window. Switching
  # backup retention between zero and non-zero reboots the instance, so it is
  # better to schedule that reboot deliberately than to have it land mid-week.
  apply_immediately = var.db_apply_immediately

  # Surfaces slow queries and errors, which are otherwise invisible.
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  lifecycle {
    # The identifier embeds a timestamp so it is unique per destroy; without
    # this, every plan would show a diff.
    ignore_changes = [final_snapshot_identifier]
  }

  tags = {
    Name = "${var.project_name}-db"
  }
}
