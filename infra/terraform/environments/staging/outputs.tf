output "vpc_id" {
  description = "Staging VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "Staging EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Staging EKS API endpoint"
  value       = module.eks.cluster_endpoint
}

output "database_endpoint" {
  description = "Staging PostgreSQL endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Staging Redis endpoint"
  value       = module.elasticache.endpoint
}
