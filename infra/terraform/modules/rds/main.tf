# PWBS – RDS Module (TASK-146)
# PostgreSQL 16 auf RDS mit Read Replica und Connection Pooling via RDS Proxy

# ---------------------------------------------------------------------------
# Subnet Group
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.environment}-db"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-db-subnet" })
}

# ---------------------------------------------------------------------------
# Security Group
# ---------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name_prefix = "${var.project}-${var.environment}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.app_security_group_ids
    description     = "PostgreSQL from app tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-rds-sg" })
}

# ---------------------------------------------------------------------------
# Parameter Group
# ---------------------------------------------------------------------------

resource "aws_db_parameter_group" "postgres16" {
  name   = "${var.project}-${var.environment}-pg16"
  family = "postgres16"

  parameter {
    name  = "max_connections"
    value = "200"
  }

  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Primary Instance
# ---------------------------------------------------------------------------

resource "aws_db_instance" "primary" {
  identifier     = "${var.project}-${var.environment}-primary"
  engine         = "postgres"
  engine_version = "16.4"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = var.kms_key_arn

  db_name  = "pwbs"
  username = "pwbs_admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.postgres16.name

  multi_az            = var.environment == "production"
  publicly_accessible = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  deletion_protection = var.environment == "production"
  skip_final_snapshot = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.project}-${var.environment}-final" : null

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-primary" })
}

# ---------------------------------------------------------------------------
# Read Replica
# ---------------------------------------------------------------------------

resource "aws_db_instance" "read_replica" {
  count = var.enable_read_replica ? 1 : 0

  identifier          = "${var.project}-${var.environment}-read-replica"
  replicate_source_db = aws_db_instance.primary.identifier
  instance_class      = var.replica_instance_class
  storage_encrypted   = true
  kms_key_id          = var.kms_key_arn

  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.postgres16.name

  publicly_accessible = false
  skip_final_snapshot = true

  tags = merge(var.tags, { Name = "${var.project}-${var.environment}-read-replica" })
}

# ---------------------------------------------------------------------------
# RDS Proxy (Connection Pooling – replaces PgBouncer)
# ---------------------------------------------------------------------------

resource "aws_db_proxy" "main" {
  name                   = "${var.project}-${var.environment}-proxy"
  debug_logging          = false
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = var.rds_proxy_role_arn
  vpc_security_group_ids = [aws_security_group.rds.id]
  vpc_subnet_ids         = var.private_subnet_ids

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "DISABLED"
    secret_arn  = var.db_credentials_secret_arn
  }

  tags = var.tags
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    max_connections_percent      = 80
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

resource "aws_db_proxy_target" "main" {
  db_instance_identifier = aws_db_instance.primary.identifier
  db_proxy_name          = aws_db_proxy.main.name
  target_group_name      = aws_db_proxy_default_target_group.main.name
}
