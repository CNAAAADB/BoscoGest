# ──────────────────────────────────────────────
# Route 53 — DNS for a domain registered outside AWS
# ──────────────────────────────────────────────
#
# The registrar keeps ownership of the domain; only the nameservers move. After
# the first apply, read `terraform output route53_nameservers` and set those
# four values as the domain's nameservers at the registrar. Propagation takes
# anywhere from minutes to 48 hours, so do it as early as possible.
#
# Everything here is inert until both `domain_name` and `create_route53_zone`
# are set, so it can be committed and reviewed before the domain exists.

resource "aws_route53_zone" "main" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  name    = var.domain_name
  comment = "Managed by Terraform — ${var.project_name}"

  tags = {
    Name = "${var.project_name}-zone"
  }
}

# ──────────────────────────────────────────────
# ACM certificate validation
# ──────────────────────────────────────────────
#
# Replaces the manual "copy these CNAMEs into the registrar" step: with the
# zone here, validation records are published and the certificate issues on its
# own, usually within a couple of minutes.

resource "aws_route53_record" "acm_validation" {
  for_each = (var.domain_name != "" && var.create_route53_zone) ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  zone_id         = aws_route53_zone.main[0].zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 60
  records         = [each.value.record]
}

resource "aws_acm_certificate_validation" "frontend" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for r in aws_route53_record.acm_validation : r.fqdn]
}

# ──────────────────────────────────────────────
# Front-end aliases
# ──────────────────────────────────────────────

resource "aws_route53_record" "apex" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# REQ-TEN-03: every entity is reachable at {entity}.<domain>. A wildcard record
# means adding an entity needs no DNS change at all — without it, each new
# association would require a manual record.
resource "aws_route53_record" "wildcard" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "*.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────
#
# Points straight at the instance's Elastic IP. TLS is terminated on the
# instance by Caddy, which obtains a Let's Encrypt certificate for this name —
# so this record must resolve before Caddy is started, or the ACME challenge
# fails.

resource "aws_route53_record" "api" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "api.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.backend.public_ip]
}
