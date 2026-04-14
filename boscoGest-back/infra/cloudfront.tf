# ──────────────────────────────────────────────
# CloudFront + ACM for custom domain
#
# Only created when var.domain_name is set.
# Requires DNS validation: after terraform apply,
# add the CNAME records shown in the outputs to
# your domain registrar.
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# ACM Certificate (must be in us-east-1 for CloudFront)
# ──────────────────────────────────────────────

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "frontend" {
  count    = var.domain_name != "" ? 1 : 0
  provider = aws.us_east_1

  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-frontend-cert"
  }
}

# ──────────────────────────────────────────────
# Reference the existing frontend S3 bucket
# ──────────────────────────────────────────────

data "aws_s3_bucket" "frontend" {
  count  = var.domain_name != "" ? 1 : 0
  bucket = var.frontend_bucket_name
}

# ──────────────────────────────────────────────
# CloudFront Distribution
# ──────────────────────────────────────────────

resource "aws_cloudfront_distribution" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  aliases             = [var.domain_name, "www.${var.domain_name}"]
  price_class         = "PriceClass_100" # Only US + Europe (cheapest)

  # Origin: S3 website endpoint (HTTP only)
  origin {
    domain_name = "${var.frontend_bucket_name}.s3-website-${var.aws_region}.amazonaws.com"
    origin_id   = "S3-frontend"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    # Cache 24h, but allow S3 headers to override
    min_ttl     = 0
    default_ttl = 86400
    max_ttl     = 31536000
  }

  # SPA routing: return index.html for 403/404
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.frontend[0].arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "${var.project_name}-frontend-cdn"
  }

  # Wait for certificate validation before creating
  depends_on = [aws_acm_certificate.frontend]
}
