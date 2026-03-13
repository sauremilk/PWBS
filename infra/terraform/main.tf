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
  source            = "./modules/rds"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  db_password       = var.db_password
}

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
}

#  EC2 (Weaviate) 
module "ec2_weaviate" {
  source            = "./modules/ec2_weaviate"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
}

#  EC2 (Neo4j) 
module "ec2_neo4j" {
  source            = "./modules/ec2_neo4j"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
}

#  ElastiCache (Redis) 
module "elasticache" {
  source            = "./modules/elasticache"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
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