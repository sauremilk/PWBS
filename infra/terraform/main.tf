# PWBS  Terraform Root Module
# AWS-Infrastruktur fuer das Persoenliche Wissens-Betriebssystem
#
# Region: eu-central-1 (Frankfurt)  DSGVO-konform

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "pwbs-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "eu-central-1"
    encrypt        = true
    dynamodb_table = "pwbs-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "PWBS"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

#  Networking
module "networking" {
  source      = "./modules/networking"
  environment = var.environment
  project     = var.project
}

#  RDS (PostgreSQL)
module "rds" {
  source              = "./modules/rds"
  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  db_password         = var.db_password
  kms_key_arn         = module.kms.key_arn
  app_security_group_ids  = [module.ecs.api_security_group_id]
  enable_read_replica     = var.environment == "production"
  rds_proxy_role_arn      = var.rds_proxy_role_arn
  db_credentials_secret_arn = var.db_credentials_secret_arn
#  ECS (Fargate  Backend API)
module "ecs" {
  source             = "./modules/ecs"
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  public_subnet_ids  = module.networking.public_subnet_ids
  database_url       = module.rds.connection_url
  weaviate_url       = "http://${module.ec2_weaviate.private_ip}:8080"
  neo4j_uri          = "bolt://${module.ec2_neo4j.private_ip}:7687"
  redis_url          = module.elasticache.connection_url
  kms_key_arn        = module.kms.key_arn
  acm_certificate_arn = var.acm_certificate_arn
  execution_role_arn  = var.ecs_execution_role_arn
  task_role_arn       = var.ecs_task_role_arn
  api_desired_count   = var.environment == "production" ? 3 : 1
  source            = "./modules/ec2_neo4j"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
}

#  ElastiCache (Redis)
module "elasticache" {
  source             = "./modules/elasticache"
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  subnet_group_name  = module.networking.vpc_id  # wird durch Networking-Output ersetzt
  security_group_ids = [module.ecs.api_security_group_id]
  auth_token         = var.redis_auth_token
  num_cache_clusters = var.environment == "production" ? 2 : 1
}

#  CloudFront (CDN)
module "cloudfront" {
  source              = "./modules/cloudfront"
  environment         = var.environment
  api_alb_dns_name    = module.ecs.alb_dns_name
  acm_certificate_arn = var.cloudfront_certificate_arn
  domain_aliases      = var.domain_aliases
}

#  KMS (Envelope Encryption)
module "kms" {
  source      = "./modules/kms"
  environment = var.environment
}

#  Monitoring (CloudWatch)
module "monitoring" {
  source      = "./modules/monitoring"
  environment = var.environment
  ecs_cluster = module.ecs.cluster_name
}
