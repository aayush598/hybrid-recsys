###############################################################################
# BeautyRec Production Environment
# Wires VPC, EKS, RDS, and ElastiCache modules together
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  backend "s3" {
    bucket         = "beautyrec-tfstate"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "beautyrec-tfstate-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "beautyrec"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-production"
}

# -----------------------------------------------------------------------------
# VPC
# -----------------------------------------------------------------------------

module "vpc" {
  source = "../../modules/vpc"

  project_name      = var.project_name
  environment       = "production"
  vpc_cidr          = var.vpc_cidr
  az_count          = 3
  high_availability = true

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# EKS
# -----------------------------------------------------------------------------

module "eks" {
  source = "../../modules/eks"

  project_name        = var.project_name
  environment         = "production"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  public_subnet_ids   = module.vpc.public_subnet_ids
  kubernetes_version  = var.kubernetes_version
  node_instance_type  = var.node_instance_type
  capacity_type       = "ON_DEMAND"
  desired_size        = 4
  min_size            = 3
  max_size            = 12

  endpoint_public_access_cidrs = var.admin_cidr_blocks

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL (Multi-AZ, encrypted, read replica)
# -----------------------------------------------------------------------------

module "rds" {
  source = "../../modules/rds"

  project_name           = var.project_name
  environment            = "production"
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  allowed_security_groups = [module.eks.node_security_group_id]

  instance_class             = var.db_instance_class
  multi_az                   = true
  create_read_replica        = true
  allocated_storage          = 100
  max_allocated_storage      = 1000
  backup_retention_days      = 30
  deletion_protection        = true
  performance_insights_enabled = true
  max_connections            = 400

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# ElastiCache Redis (Multi-AZ failover)
# -----------------------------------------------------------------------------

module "elasticache" {
  source = "../../modules/elasticache"

  project_name                 = var.project_name
  environment                  = "production"
  vpc_id                       = module.vpc.vpc_id
  private_subnet_ids           = module.vpc.private_subnet_ids
  allowed_security_groups      = [module.eks.node_security_group_id]
  node_type                    = var.redis_node_type
  num_cache_nodes              = 2
  automatic_failover_enabled   = true
  multi_az_enabled             = true
  snapshot_retention_limit     = 14
  transit_encryption_enabled   = true

  tags = local.common_tags
}
