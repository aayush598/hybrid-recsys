variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "beautyrec"
}

variable "environment" {
  description = "Environment name (production, staging)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC hosting the cluster"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for worker nodes"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for load balancers"
  type        = list(string)
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "node_instance_type" {
  description = "EC2 instance type for the default node group"
  type        = string
  default     = "m6i.large"
}

variable "node_disk_size" {
  description = "Root EBS volume size (GiB) for worker nodes"
  type        = number
  default     = 50
}

variable "capacity_type" {
  description = "Capacity type: ON_DEMAND or SPOT"
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.capacity_type)
    error_message = "capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 3
}

variable "min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 2
}

variable "max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 10
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public cluster endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
