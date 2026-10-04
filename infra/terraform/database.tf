# Aurora PostgreSQL Serverless v2. Holds the governance schema and the pgvector knowledge index.
# The master password is generated and rotated by RDS in Secrets Manager.

resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "PostgreSQL from API tasks only"
  vpc_id      = aws_vpc.main.id
  ingress {
    description     = "PostgreSQL from API tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }
}

resource "aws_kms_key" "data" {
  description         = "${local.name} database and secrets encryption"
  enable_key_rotation = true
}

resource "aws_rds_cluster_parameter_group" "main" {
  name   = "${local.name}-pg16"
  family = "aurora-postgresql16"
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

resource "aws_rds_cluster" "main" {
  cluster_identifier                  = local.name
  engine                              = "aurora-postgresql"
  engine_mode                         = "provisioned"
  engine_version                      = "16.6"
  database_name                       = "aegis"
  master_username                     = "aegis_admin"
  manage_master_user_password         = true
  master_user_secret_kms_key_id       = aws_kms_key.data.key_id
  db_subnet_group_name                = aws_db_subnet_group.main.name
  vpc_security_group_ids              = [aws_security_group.db.id]
  db_cluster_parameter_group_name     = aws_rds_cluster_parameter_group.main.name
  storage_encrypted                   = true
  kms_key_id                          = aws_kms_key.data.arn
  backup_retention_period             = 14
  preferred_backup_window             = "07:00-08:00"
  copy_tags_to_snapshot               = true
  deletion_protection                 = var.deletion_protection
  skip_final_snapshot                 = !var.deletion_protection
  final_snapshot_identifier           = var.deletion_protection ? "${local.name}-final" : null
  enabled_cloudwatch_logs_exports     = ["postgresql"]
  iam_database_authentication_enabled = true

  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_acu
    max_capacity = var.aurora_max_acu
  }
}

resource "aws_rds_cluster_instance" "main" {
  count                           = 2 # writer plus one reader in a second AZ
  identifier                      = "${local.name}-${count.index}"
  cluster_identifier              = aws_rds_cluster.main.id
  instance_class                  = "db.serverless"
  engine                          = aws_rds_cluster.main.engine
  engine_version                  = aws_rds_cluster.main.engine_version
  db_subnet_group_name            = aws_db_subnet_group.main.name
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.data.arn
}
