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

# ──────────────────────────────────────────────
# Origin Access Control
# ──────────────────────────────────────────────
#
# Lets CloudFront sign its requests to S3, so the bucket can stay private and
# CloudFront becomes the only way in.

resource "aws_cloudfront_origin_access_control" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  name                              = "${var.project_name}-frontend-oac"
  description                       = "Signed access from CloudFront to the frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ──────────────────────────────────────────────
# Security headers
# ──────────────────────────────────────────────
#
# The nginx image sets some of these, but production serves the SPA from
# S3+CloudFront and never runs that nginx, so in practice none of them were
# being sent.

resource "aws_cloudfront_response_headers_policy" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  name = "${var.project_name}-security-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = false
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    content_security_policy {
      override = true
      # Angular needs inline styles for component encapsulation. connect-src
      # has to name the API host explicitly, including the wss:// origin the
      # chat and notification sockets use.
      content_security_policy = join("; ", [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https://${var.frontend_bucket_name}.s3.${var.aws_region}.amazonaws.com",
        "connect-src 'self' https://api.${var.domain_name} wss://api.${var.domain_name}",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ])
    }
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  # The wildcard is what makes REQ-TEN-03 work: each entity is served at
  # {entity}.<domain>. The ACM certificate already covers *.<domain>, but
  # without the alias CloudFront rejects those hostnames.
  aliases     = [var.domain_name, "www.${var.domain_name}", "*.${var.domain_name}"]
  price_class = "PriceClass_100" # Only US + Europe (cheapest)

  # Origin: the S3 REST endpoint, reached with Origin Access Control.
  #
  # This previously pointed at the bucket's *website* endpoint over http-only,
  # which meant the CloudFront-to-origin leg was unencrypted and, worse, the
  # bucket had to stay publicly readable — so anyone could bypass CloudFront
  # (and its TLS, headers and caching) by hitting the bucket directly.
  #
  # The REST endpoint has no index/error document behaviour, so SPA routing
  # relies on the custom_error_response rules below mapping 403/404 to
  # /index.html.
  origin {
    domain_name              = "${var.frontend_bucket_name}.s3.${var.aws_region}.amazonaws.com"
    origin_id                = "S3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend[0].id
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = "S3-frontend"
    viewer_protocol_policy     = "redirect-to-https"
    compress                   = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend[0].id

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

  # CloudFront rejects a certificate that is not yet ISSUED, so this must wait
  # for validation to complete, not merely for the certificate to be requested.
  depends_on = [
    aws_acm_certificate.frontend,
    aws_acm_certificate_validation.frontend,
  ]
}
