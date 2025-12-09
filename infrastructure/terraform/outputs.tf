# Outputs for Optimus Terraform infrastructure

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

# EKS Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "node_groups" {
  description = "EKS node groups"
  value       = module.eks.eks_managed_node_groups
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider for EKS"
  value       = module.eks.oidc_provider_arn
}

# Database Outputs
output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "db_instance_name" {
  description = "RDS instance name"
  value       = module.rds.db_instance_name
}

output "db_instance_username" {
  description = "RDS instance username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "db_subnet_group_name" {
  description = "Name of the database subnet group"
  value       = aws_db_subnet_group.main.name
}

# Redis Outputs
output "redis_cluster_address" {
  description = "Address of the Redis cluster"
  value       = module.redis.cluster_address
}

output "redis_cluster_port" {
  description = "Port of the Redis cluster"
  value       = module.redis.cluster_port
}

output "redis_parameter_group_name" {
  description = "Name of the Redis parameter group"
  value       = module.redis.parameter_group_name
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "The DNS name of the load balancer"
  value       = module.alb.lb_dns_name
}

output "alb_zone_id" {
  description = "The canonical hosted zone ID of the load balancer"
  value       = module.alb.lb_zone_id
}

output "alb_arn" {
  description = "The ARN of the load balancer"
  value       = module.alb.lb_arn
}

output "target_group_arns" {
  description = "ARNs of the target groups"
  value       = module.alb.target_group_arns
}

# Certificate Outputs
output "acm_certificate_arn" {
  description = "The ARN of the certificate"
  value       = module.acm.acm_certificate_arn
}

output "acm_certificate_domain_validation_options" {
  description = "Domain validation options for the certificate"
  value       = module.acm.acm_certificate_domain_validation_options
}

# S3 Outputs
output "s3_bucket_id" {
  description = "Name of the S3 bucket"
  value       = module.s3.s3_bucket_id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = module.s3.s3_bucket_arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = module.s3.s3_bucket_bucket_domain_name
}

# DNS Outputs
output "route53_record_app" {
  description = "Route53 record for main application"
  value       = aws_route53_record.app.fqdn
}

output "route53_record_api" {
  description = "Route53 record for API"
  value       = aws_route53_record.api.fqdn
}

# Security Outputs
output "kms_key_arn" {
  description = "ARN of the KMS key for EKS encryption"
  value       = aws_kms_key.eks.arn
}

output "kms_key_alias" {
  description = "Alias of the KMS key"
  value       = aws_kms_alias.eks.name
}

# IAM Outputs
output "rds_enhanced_monitoring_role_arn" {
  description = "ARN of the RDS enhanced monitoring role"
  value       = aws_iam_role.rds_enhanced_monitoring.arn
}

# Connection Information
output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${var.database_username}:${random_password.db_password.result}@${module.rds.db_instance_endpoint}/${var.database_name}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://${module.redis.cluster_address}:${module.redis.cluster_port}"
}

# Application URLs
output "application_url" {
  description = "Application URL"
  value       = "https://${var.domain_name}"
}

output "api_url" {
  description = "API URL"
  value       = "https://api.${var.domain_name}"
}

output "monitoring_url" {
  description = "Monitoring URL (Grafana)"
  value       = "https://monitoring.${var.domain_name}"
}

# Kubernetes Configuration
output "kubectl_config" {
  description = "kubectl config command to configure local kubectl"
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_name}"
}

# Environment Configuration for Applications
output "environment_config" {
  description = "Environment configuration for applications"
  value = {
    DATABASE_URL = "postgresql://${var.database_username}:${random_password.db_password.result}@${module.rds.db_instance_endpoint}/${var.database_name}"
    REDIS_URL    = "redis://${module.redis.cluster_address}:${module.redis.cluster_port}"
    AWS_REGION   = var.aws_region
    ENVIRONMENT  = var.environment
    DOMAIN_NAME  = var.domain_name
    S3_BUCKET    = module.s3.s3_bucket_id
    KMS_KEY_ARN  = aws_kms_key.eks.arn
  }
  sensitive = true
}