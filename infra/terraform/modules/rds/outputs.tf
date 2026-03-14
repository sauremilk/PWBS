output "endpoint" { value = aws_db_instance.primary.endpoint }
output "connection_url" {
  value     = "postgresql+asyncpg://pwbs_admin:${var.db_password}@${aws_db_proxy.main.endpoint}:5432/pwbs"
  sensitive = true
}
output "proxy_endpoint" { value = aws_db_proxy.main.endpoint }
output "read_replica_endpoint" {
  value = var.enable_read_replica ? aws_db_instance.read_replica[0].endpoint : ""
}
output "security_group_id" { value = aws_security_group.rds.id }
