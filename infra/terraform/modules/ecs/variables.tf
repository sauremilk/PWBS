variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "database_url" { type = string; sensitive = true }
variable "weaviate_url" { type = string }
variable "neo4j_uri" { type = string }
variable "redis_url" { type = string }
variable "kms_key_arn" { type = string }
