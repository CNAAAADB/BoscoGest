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
