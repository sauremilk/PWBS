# PWBS  Terraform Variables

variable "aws_region" {
  description = "AWS Region (eu-central-1 fuer DSGVO-Konformitaet)"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Deployment-Umgebung (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment muss staging oder production sein."
  }
}

variable "project" {
  description = "Projektname fuer Tagging"
  type        = string
  default     = "pwbs"
}

variable "db_password" {
  description = "PostgreSQL Master-Passwort"
  type        = string
  sensitive   = true
}

# --- Horizontale Skalierung (TASK-146) ---

variable "acm_certificate_arn" {
  description = "ACM certificate ARN fuer ALB HTTPS (eu-central-1)"
  type        = string
}

variable "cloudfront_certificate_arn" {
  description = "ACM certificate ARN fuer CloudFront (muss in us-east-1 liegen)"
  type        = string
}

variable "domain_aliases" {
  description = "Custom Domain-Aliase fuer CloudFront"
  type        = list(string)
  default     = []
}

variable "ecs_execution_role_arn" {
  description = "IAM Role ARN fuer ECS Task Execution"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "IAM Role ARN fuer ECS Task"
  type        = string
}

variable "rds_proxy_role_arn" {
  description = "IAM Role ARN fuer RDS Proxy"
  type        = string
}

variable "db_credentials_secret_arn" {
  description = "Secrets Manager ARN fuer DB-Credentials (RDS Proxy)"
  type        = string
}

variable "redis_auth_token" {
  description = "Auth-Token fuer ElastiCache Redis"
  type        = string
  sensitive   = true
}
