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

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# --- Networking ---

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (RDS)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# --- EC2 ---

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of the SSH key pair (must exist in AWS)"
  type        = string
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH into the EC2 instance"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# --- RDS ---

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "boscogest"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "boscogest_admin"
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

# --- App ---

variable "secret_key" {
  description = "JWT secret key (min 32 chars)"
  type        = string
  sensitive   = true
}

variable "cors_origins" {
  description = "Comma-separated CORS origins"
  type        = string
  default     = "*"
}

variable "docker_image" {
  description = "Docker image for the backend (e.g. from ECR or Docker Hub)"
  type        = string
  default     = ""
}

variable "frontend_url" {
  description = "URL of the frontend (for CORS)"
  type        = string
  default     = ""
}

# --- Domain ---

variable "domain_name" {
  description = "Custom domain name (e.g. boscogest.com). Leave empty to skip CloudFront/ACM setup."
  type        = string
  default     = ""
}

variable "frontend_bucket_name" {
  description = "Name of the S3 bucket hosting the frontend"
  type        = string
  default     = "boscogest-frontend"
}
