variable "aws_region" {
  description = "AWS region for staging resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "beautyrec"
}

variable "vpc_cidr" {
  description = "CIDR block for the staging VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "t4g.medium"
}

variable "db_instance_class" {
  description = "RDS instance class for staging"
  type        = string
  default     = "db.t4g.medium"
}

variable "redis_node_type" {
  description = "ElastiCache node type for staging"
  type        = string
  default     = "cache.t4g.small"
}

variable "admin_cidr_blocks" {
  description = "CIDR blocks allowed to reach the EKS public endpoint"
  type        = list(string)
  default     = []
}
