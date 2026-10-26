output "ec2_public_ip" {
  description = "Static public IP of the backend EC2 instance (Elastic IP)"
  value       = aws_eip.backend.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the backend EC2 instance"
  value       = aws_eip.backend.public_dns
}

output "api_url" {
  description = "Backend API URL"
  value       = "http://${aws_eip.backend.public_ip}:8000"
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  description = "RDS PostgreSQL address (without port)"
  value       = aws_db_instance.postgres.address
}

output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql+psycopg2://${var.db_username}:****@${aws_db_instance.postgres.endpoint}/${var.db_name}"
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

# ──────────────────────────────────────────────
# S3
# ──────────────────────────────────────────────

output "s3_bucket_name" {
  description = "S3 bucket name for file uploads"
  value       = aws_s3_bucket.uploads.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.uploads.arn
}

# ──────────────────────────────────────────────
# ECR
# ──────────────────────────────────────────────

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

# ──────────────────────────────────────────────
# CloudFront / Domain
# ──────────────────────────────────────────────

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = var.domain_name != "" ? aws_cloudfront_distribution.frontend[0].domain_name : "N/A (no domain configured)"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = var.domain_name != "" ? aws_cloudfront_distribution.frontend[0].id : "N/A"
}

output "acm_dns_validation_records" {
  description = "DNS CNAME records to add at your domain registrar for certificate validation"
  value = var.domain_name != "" ? [
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ] : []
}

output "dns_records_to_add" {
  description = "DNS records to configure at your domain registrar"
  value = var.domain_name != "" ? join("\n", [
    "Add these records at your domain registrar:",
    "",
    "1. Certificate validation (from acm_dns_validation_records output)",
    "2. CNAME: www.${var.domain_name} → ${aws_cloudfront_distribution.frontend[0].domain_name}",
    "3. ALIAS/ANAME: ${var.domain_name} → ${aws_cloudfront_distribution.frontend[0].domain_name}",
    "   (If your registrar doesn't support ALIAS, migrate nameservers to Route 53)",
  ]) : "N/A (no domain configured)"
}

output "frontend_url_with_domain" {
  description = "Frontend URL with custom domain"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${var.frontend_bucket_name}.s3-website-${var.aws_region}.amazonaws.com"
}

output "ecr_push_commands" {
  description = "Commands to build, tag and push the Docker image to ECR"
  value       = <<-EOT
    # Login to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.backend.repository_url}

    # Build, tag and push
    docker build -t ${var.project_name}-back .
    docker tag ${var.project_name}-back:latest ${aws_ecr_repository.backend.repository_url}:latest
    docker push ${aws_ecr_repository.backend.repository_url}:latest
  EOT
}

# ──────────────────────────────────────────────
# DNS / email
# ──────────────────────────────────────────────

output "route53_nameservers" {
  description = "Set these four as the domain's nameservers at the registrar."
  value       = var.create_route53_zone && var.domain_name != "" ? aws_route53_zone.main[0].name_servers : []
}

output "ses_configuration_set" {
  description = "Value for the SES_CONFIGURATION_SET environment variable."
  value       = aws_sesv2_configuration_set.transactional.configuration_set_name
}

output "ses_events_topic_arn" {
  description = "SNS topic receiving SES bounce/complaint/reject events."
  value       = aws_sns_topic.ses_events.arn
}

output "ses_dkim_tokens" {
  description = "DKIM CNAME tokens. Only needed when DNS is kept at the registrar."
  value       = var.domain_name != "" ? aws_sesv2_email_identity.domain[0].dkim_signing_attributes[0].tokens : []
}

output "cloudfront_distribution_arn" {
  description = <<-DESC
    Feed this into the frontend state as cloudfront_distribution_arn so its
    bucket policy can grant CloudFront (and only CloudFront) read access.
  DESC
  value       = var.domain_name != "" ? aws_cloudfront_distribution.frontend[0].arn : ""
}
