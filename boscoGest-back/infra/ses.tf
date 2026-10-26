# ──────────────────────────────────────────────
# SES — transactional email (welcome messages)
# ──────────────────────────────────────────────
#
# Sending identities:
#   * While no domain is registered, senders are verified one address at a
#     time from the console/CLI (an EMAIL_ADDRESS identity). Those are not
#     managed here because they are throwaway.
#   * Once `domain_name` is set, the domain identity below is created with
#     DKIM, which is what makes mail from noreply@<domain> pass DMARC.

# ──────────────────────────────────────────────
# Bounce / complaint feedback
# ──────────────────────────────────────────────
#
# Keeping production sending access requires reacting to bounces and
# complaints. The account-level suppression list already blocks further
# delivery to a hard-bounced or complaining address; this topic makes those
# events observable so they can be acted on rather than silently dropped.

resource "aws_sns_topic" "ses_events" {
  name = "${var.project_name}-ses-events"

  tags = {
    Name = "${var.project_name}-ses-events"
  }
}

resource "aws_sesv2_configuration_set" "transactional" {
  configuration_set_name = "${var.project_name}-transactional"

  delivery_options {
    tls_policy = "REQUIRE"
  }

  reputation_options {
    reputation_metrics_enabled = true
  }

  sending_options {
    sending_enabled = true
  }

  suppression_options {
    # Never attempt delivery to an address that already hard-bounced or
    # complained.
    suppressed_reasons = ["BOUNCE", "COMPLAINT"]
  }
}

resource "aws_sesv2_configuration_set_event_destination" "sns" {
  configuration_set_name = aws_sesv2_configuration_set.transactional.configuration_set_name
  event_destination_name = "${var.project_name}-sns-events"

  event_destination {
    enabled              = true
    matching_event_types = ["BOUNCE", "COMPLAINT", "REJECT", "DELIVERY_DELAY"]

    sns_destination {
      topic_arn = aws_sns_topic.ses_events.arn
    }
  }
}

# ──────────────────────────────────────────────
# Domain identity (created only once a domain exists)
# ──────────────────────────────────────────────

resource "aws_sesv2_email_identity" "domain" {
  count = var.domain_name == "" ? 0 : 1

  email_identity = var.domain_name

  dkim_signing_attributes {
    next_signing_key_length = "RSA_2048_BIT"
  }

  tags = {
    Name = "${var.project_name}-ses-domain"
  }
}

# Publishing these three CNAMEs is what verifies the domain and enables DKIM.
# With Route 53 holding the zone they are created automatically; without it
# they have to be added at the registrar by hand.
resource "aws_route53_record" "ses_dkim" {
  count = var.domain_name != "" && var.create_route53_zone ? 3 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "${aws_sesv2_email_identity.domain[0].dkim_signing_attributes[0].tokens[count.index]}._domainkey.${var.domain_name}"
  type    = "CNAME"
  ttl     = 600
  records = ["${aws_sesv2_email_identity.domain[0].dkim_signing_attributes[0].tokens[count.index]}.dkim.amazonses.com"]
}

# Tells receiving servers that SES is allowed to send for this domain.
resource "aws_route53_record" "ses_spf" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "TXT"
  ttl     = 600
  records = ["v=spf1 include:amazonses.com ~all"]
}

# Without a DMARC record, DKIM and SPF are advisory only. "quarantine" is the
# usual starting point: it asks receivers to treat unauthenticated mail as
# suspicious without discarding it outright.
resource "aws_route53_record" "ses_dmarc" {
  count = var.domain_name != "" && var.create_route53_zone ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "_dmarc.${var.domain_name}"
  type    = "TXT"
  ttl     = 600
  records = ["v=DMARC1; p=quarantine; rua=mailto:${var.dmarc_report_email}"]
}
