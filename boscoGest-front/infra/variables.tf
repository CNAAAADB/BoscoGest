variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "boscogest"
}

variable "bucket_name" {
  description = "S3 bucket name (must be globally unique)"
  type        = string
}

variable "cloudfront_distribution_arn" {
  description = <<-DESC
    ARN of the CloudFront distribution allowed to read this bucket. Comes from
    the backend state: `terraform output cloudfront_distribution_arn`. While it
    is empty no bucket policy is written, which leaves the bucket private and
    unreadable — expected before the distribution exists.
  DESC
  type        = string
  default     = ""
}
