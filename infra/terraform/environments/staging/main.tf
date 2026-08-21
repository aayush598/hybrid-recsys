###############################################################################
# BeautyRec Staging Environment
# Reduced-cost mirror of production for pre-release validation
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
    key            = "staging/terraform.tfstate"
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
      Environment = "staging"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-staging"

  common_tags = {
    Project     = var.project_name
    Environment = "staging"
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------------
# VPC (2 AZs, single shared NAT gateway to cut cost)
# -----------------------------------------------------------------------------

module "vpc" {
  source = "../../modules/vpc"

  project_name      = var.project_name
  environment       = "staging"
  vpc_cidr          = var.vpc_cidr
  az_count          = 2
  high_availability = false

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# EKS (spot capacity, small node group)
# -----------------------------------------------------------------------------

module "eks" {
  source = "../../modules/eks"

  project_name        = var.project_name
  environment         = "staging"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  public_subnet_ids   = module.vpc.public_subnet_ids
  kubernetes_version  = var.kubernetes_version
  node_instance_type  = var.node_instance_type
  capacity_type       = "SPOT"
  node_disk_size      = 30
  desired_size        = 1
  min_size            = 1
  max_size            = 4
  log_retention_days  = 7

  endpoint_public_access_cidrs = var.admin_cidr_blocks

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL (single-AZ, no read replica, short backups)
# -----------------------------------------------------------------------------

module "rds" {
  source = "../../modules/rds"

  project_name            = var.project_name
  environment             = "staging"
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  allowed_security_groups = [module.eks.node_security_group_id]

  instance_class               = var.db_instance_class
  multi_az                     = false
  create_read_replica          = false
  allocated_storage            = 20
  max_allocated_storage        = 100
  backup_retention_days        = 3
  deletion_protection          = false
  performance_insights_enabled = false
  max_connections              = 100

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# ElastiCache Redis (single node, no failover)
# -----------------------------------------------------------------------------

module "elasticache" {
  source = "../../modules/elasticache"

  project_name                 = var.project_name
  environment                  = "staging"
  vpc_id                       = module.vpc.vpc_id
  private_subnet_ids           = module.vpc.private_subnet_ids
  allowed_security_groups      = [module.eks.node_security_group_id]
  node_type                    = var.redis_node_type
  num_cache_nodes              = 1
  automatic_failover_enabled   = false
  multi_az_enabled             = false
  snapshot_retention_limit     = 1
  transit_encryption_enabled   = true

  tags = local.common_tags
}
