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
  description = "ID of the VPC hosting the database"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the DB subnet group"
  type        = list(string)
}

variable "allowed_security_groups" {
  description = "Security groups allowed to reach the database"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to reach the database"
  type        = list(string)
  default     = []
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.7"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "database_name" {
  description = "Initial database name"
  type        = string
  default     = "beautyrec"
}

variable "master_username" {
  description = "Master username for the database"
  type        = string
  default     = "beautyrec_admin"
}

variable "allocated_storage" {
  description = "Initial storage in GiB"
  type        = number
  default     = 50
}

variable "max_allocated_storage" {
  description = "Storage autoscaling upper bound in GiB"
  type        = number
  default     = 500
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment for high availability"
  type        = bool
  default     = true
}

variable "create_read_replica" {
  description = "Provision a read replica for reporting/failover reads"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention in days"
  type        = number
  default     = 14
}

variable "deletion_protection" {
  description = "Enable deletion protection on the instance"
  type        = bool
  default     = true
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "max_connections" {
  description = "max_connections parameter value"
  type        = number
  default     = 200
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
