output "vpc_id" {
  description = "Production VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "Production EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Production EKS API endpoint"
  value       = module.eks.cluster_endpoint
}

output "database_endpoint" {
  description = "Production PostgreSQL endpoint"
  value       = module.rds.endpoint
}

output "database_replica_endpoint" {
  description = "Production PostgreSQL read replica endpoint"
  value       = module.rds.replica_endpoint
}

output "redis_endpoint" {
  description = "Production Redis endpoint"
  value       = module.elasticache.endpoint
}

output "database_master_secret_arn" {
  description = "Secrets Manager ARN for DB master credentials"
  value       = module.rds.master_secret_arn
  sensitive   = true
}
