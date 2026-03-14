output "endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "connection_url" {
  value     = "rediss://:${var.auth_token}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
  sensitive = true
}
