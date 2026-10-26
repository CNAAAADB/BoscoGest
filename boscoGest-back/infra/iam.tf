data "aws_caller_identity" "current" {}

# ──────────────────────────────────────────────
# IAM Role for EC2 (ECR pull access)
# ──────────────────────────────────────────────

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2" {
  name               = "${var.project_name}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Name = "${var.project_name}-ec2-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# ──────────────────────────────────────────────
# S3 uploads bucket access
# ──────────────────────────────────────────────

resource "aws_iam_policy" "s3_uploads" {
  name        = "${var.project_name}-s3-uploads-policy"
  description = "Allow EC2 to read/write to the uploads S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_uploads" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.s3_uploads.arn
}

# ──────────────────────────────────────────────
# SES: transactional email (welcome emails)
# ──────────────────────────────────────────────

resource "aws_iam_policy" "ses_send" {
  name        = "${var.project_name}-ses-send-policy"
  description = "Allow the BoscoGest EC2 instance to send transactional email through SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SendTransactionalEmail"
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        # Scoped to this account and region rather than "*", so the instance
        # cannot send on behalf of identities it does not own.
        #
        # The configuration set has to be listed too. Sending *through* one is
        # a separate authorisation from sending *as* an identity, and without
        # it every call fails with AccessDenied — silently, because delivery is
        # best-effort and the failure is only logged. That is how this went
        # unnoticed until a test message was actually sent.
        Resource = [
          "arn:aws:ses:${var.aws_region}:${data.aws_caller_identity.current.account_id}:identity/*",
          "arn:aws:ses:${var.aws_region}:${data.aws_caller_identity.current.account_id}:configuration-set/*",
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ses_send" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.ses_send.arn
}
