variable "project" {
  type    = string
  default = "pwbs"
}

variable "environment" { type = string }

variable "api_alb_dns_name" {
  description = "DNS name of the API ALB for /api/* origin"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS (must be in us-east-1 for CloudFront)"
  type        = string
}

variable "domain_aliases" {
  description = "Custom domain aliases for the distribution"
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
