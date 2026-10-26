terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ──────────────────────────────────────────────
# S3 Bucket
# ──────────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket = var.bucket_name

  tags = {
    Name = "${var.project_name}-frontend"
  }
}

# ──────────────────────────────────────────────
# Static Website Hosting
# ──────────────────────────────────────────────

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html" # SPA: all routes fallback to index.html
  }
}

# ──────────────────────────────────────────────
# Access: CloudFront only
# ──────────────────────────────────────────────
#
# The bucket used to be world-readable (block_public_* all false, a policy with
# Principal = "*") and served over its plain-HTTP website endpoint. That let
# anyone bypass CloudFront and fetch the app unencrypted, which also defeated
# the security headers and the certificate.
#
# It is private now; CloudFront reaches it with Origin Access Control, and the
# policy below trusts only that one distribution.

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# The distribution lives in the backend state, so its ARN arrives as a
# variable. On a first setup that means two applies: create the distribution,
# read `terraform output cloudfront_distribution_arn` there, set it here.
resource "aws_s3_bucket_policy" "frontend" {
  count = var.cloudfront_distribution_arn == "" ? 0 : 1

  bucket = aws_s3_bucket.frontend.id

  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipalReadOnly"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = var.cloudfront_distribution_arn
          }
        }
      }
    ]
  })
}

# ──────────────────────────────────────────────
# CORS (allow API calls from the frontend)
# ──────────────────────────────────────────────

resource "aws_s3_bucket_cors_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}
