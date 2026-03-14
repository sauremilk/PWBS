variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "db_password" { type = string; sensitive = true }

variable "project" {
  type    = string
  default = "pwbs"
}

variable "instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "max_allocated_storage" {
  type    = number
  default = 100
}

variable "kms_key_arn" {
  type    = string
  default = ""
}

variable "app_security_group_ids" {
  type        = list(string)
  description = "Security group IDs allowed to connect to RDS"
  default     = []
}

variable "enable_read_replica" {
  type    = bool
  default = false
}

variable "replica_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "rds_proxy_role_arn" {
  type        = string
  description = "IAM role ARN for RDS Proxy to access Secrets Manager"
  default     = ""
}

variable "db_credentials_secret_arn" {
  type        = string
  description = "Secrets Manager secret ARN containing DB credentials"
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
