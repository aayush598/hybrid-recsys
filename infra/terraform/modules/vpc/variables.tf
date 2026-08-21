variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "beautyrec"
}

variable "environment" {
  description = "Environment name (production, staging)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be between 2 and 3."
  }
}

variable "subnet_bits" {
  description = "Extra bits for subnet CIDR sizing within the VPC"
  type        = number
  default     = 4
}

variable "high_availability" {
  description = "Provision a NAT gateway per AZ instead of a shared one"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
