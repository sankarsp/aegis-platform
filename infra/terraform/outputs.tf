output "app_url" {
  description = "Open this to use Aegis."
  value       = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "web_bucket" {
  value = aws_s3_bucket.web.bucket
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.web.id
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service" {
  value = aws_ecs_service.api.name
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

# Build-time values for the React app.
output "vite_cognito_domain" {
  value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.region}.amazoncognito.com"
}

output "vite_cognito_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "database_endpoint" {
  value = aws_rds_cluster.main.endpoint
}
