variable "aws_region" {
  description = "AWS region for production resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "beautyrec"
}

variable "vpc_cidr" {
  description = "CIDR block for the production VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "m6i.large"
}

variable "db_instance_class" {
  description = "RDS instance class for production"
  type        = string
  default     = "db.r6g.large"
}

variable "redis_node_type" {
  description = "ElastiCache node type for production"
  type        = string
  default     = "cache.r6g.large"
}

variable "admin_cidr_blocks" {
  description = "CIDR blocks allowed to reach the EKS public endpoint"
  type        = list(string)
  default     = []
}
