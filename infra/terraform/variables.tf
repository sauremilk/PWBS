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