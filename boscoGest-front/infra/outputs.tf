output "website_url" {
  description = "S3 static website URL"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.frontend.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.frontend.arn
}

output "deploy_command" {
  description = "Command to deploy the frontend to S3"
  value       = "aws s3 sync ../dist/boscoGest-front/browser/ s3://${aws_s3_bucket.frontend.id} --delete"
}
