variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "database_url" { type = string; sensitive = true }
variable "weaviate_url" { type = string }
variable "neo4j_uri" { type = string }
variable "redis_url" { type = string }
variable "kms_key_arn" { type = string }

# ALB / API (TASK-146)
variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for HTTPS on ALB"
  default     = ""
}

variable "api_cpu" {
  type    = number
  default = 1024
}

variable "api_memory" {
  type    = number
  default = 2048
}

variable "api_desired_count" {
  type        = number
  description = "Number of API task instances (3+ for horizontal scaling)"
  default     = 3
}

variable "api_environment" {
  type        = list(map(string))
  description = "Environment variables for API containers"
  default     = []
}

variable "execution_role_arn" {
  type    = string
  default = ""
}

variable "task_role_arn" {
  type    = string
  default = ""
}

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
