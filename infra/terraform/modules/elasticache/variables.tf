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
  description = "ID of the VPC hosting the cache"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the cache subnet group"
  type        = list(string)
}

variable "allowed_security_groups" {
  description = "Security groups allowed to reach the cache"
  type        = list(string)
  default     = []
}

variable "node_type" {
  description = "ElastiCache node instance type"
  type        = string
  default     = "cache.t4g.small"
}

variable "num_cache_nodes" {
  description = "Number of nodes in the cluster"
  type        = number
  default     = 1
}

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}

variable "automatic_failover_enabled" {
  description = "Enable automatic failover (requires >= 2 nodes)"
  type        = bool
  default     = false
}

variable "multi_az_enabled" {
  description = "Enable Multi-AZ with automatic failover"
  type        = bool
  default     = false
}

variable "snapshot_retention_limit" {
  description = "Number of daily snapshots to retain"
  type        = number
  default     = 7
}

variable "at_rest_encryption_enabled" {
  description = "Encrypt data at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Require TLS for connections"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
