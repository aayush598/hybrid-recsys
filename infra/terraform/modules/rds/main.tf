###############################################################################
# BeautyRec RDS Module
# PostgreSQL with Multi-AZ, encryption at rest, automated backups, read replica
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

resource "aws_security_group" "postgres" {
  name        = "${local.name_prefix}-postgres-sg"
  description = "PostgreSQL access for ${local.name_prefix}"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from allowed security groups"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  ingress {
    description = "PostgreSQL from allowed CIDR blocks"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-postgres-sg"
  })
}

# -----------------------------------------------------------------------------
# KMS encryption + credentials
# -----------------------------------------------------------------------------

resource "aws_kms_key" "rds" {
  description             = "${local.name_prefix} RDS storage encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = var.tags
}

resource "random_password" "master" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "db_master" {
  name                    = "${local.name_prefix}/rds/master-password"
  recovery_window_in_days = 7

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "db_master" {
  secret_id = aws_secretsmanager_secret.db_master.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.master.result
    engine   = "postgres"
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = var.database_name
  })
}

# -----------------------------------------------------------------------------
# Parameter / option groups
# -----------------------------------------------------------------------------

resource "aws_db_parameter_group" "main" {
  name   = "${local.name_prefix}-pg15-params"
  family = "postgres15"

  parameter {
    name  = "max_connections"
    value = tostring(var.max_connections)
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
}

# -----------------------------------------------------------------------------
# Primary instance
# -----------------------------------------------------------------------------

resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  engine                = "postgres"
  engine_version        = var.engine_version
  instance_class        = var.instance_class
  db_name               = var.database_name
  username              = var.master_username
  password              = random_password.master.result
  port                  = 5432
  db_subnet_group_name  = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  parameter_group_name  = aws_db_parameter_group.main.name

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  multi_az               = var.multi_az
  publicly_accessible    = false
  deletion_protection    = var.deletion_protection
  skip_final_snapshot    = false
  final_snapshot_identifier = "${local.name_prefix}-final-${formatdate("YYYYMMDDhhmm", timestamp())}"
  copy_tags_to_snapshot  = true

  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:30-sun:05:30"

  performance_insights_enabled = var.performance_insights_enabled
  monitoring_interval          = 60

  auto_minor_version_upgrade = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

# -----------------------------------------------------------------------------
# Optional read replica (reporting queries / failover reads)
# -----------------------------------------------------------------------------

resource "aws_db_instance" "replica" {
  count = var.create_read_replica ? 1 : 0

  identifier             = "${local.name_prefix}-postgres-replica"
  replicate_source_db    = aws_db_instance.main.arn
  instance_class         = var.instance_class
  publicly_accessible    = false
  skip_final_snapshot    = true
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.rds.arn
  vpc_security_group_ids = [aws_security_group.postgres.id]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-postgres-replica"
  })
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "endpoint" {
  description = "Connection endpoint of the primary instance"
  value       = aws_db_instance.main.address
}

output "port" {
  description = "Database port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "Initial database name"
  value       = aws_db_instance.main.db_name
}

output "replica_endpoint" {
  description = "Connection endpoint of the read replica (empty if disabled)"
  value       = var.create_read_replica ? aws_db_instance.replica[0].address : ""
}

output "security_group_id" {
  description = "Security group ID for the database"
  value       = aws_security_group.postgres.id
}

output "master_secret_arn" {
  description = "ARN of the Secrets Manager secret holding master credentials"
  value       = aws_secretsmanager_secret.db_master.arn
}
