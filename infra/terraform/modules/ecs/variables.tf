variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "database_url" { type = string; sensitive = true }
variable "weaviate_url" { type = string }
variable "neo4j_uri" { type = string }
variable "redis_url" { type = string }
variable "kms_key_arn" { type = string }

# Celery Worker variables (TASK-121)
variable "project" {
  type    = string
  default = "pwbs"
}

variable "backend_image" {
  type        = string
  description = "Docker image URI for backend/worker containers"
  default     = ""
}

variable "worker_environment" {
  type        = list(map(string))
  description = "Environment variables for Celery worker containers"
  default     = []
}

variable "log_group" {
  type    = string
  default = "/ecs/pwbs"
}

variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "tags" {
  type    = map(string)
  default = {}
}
