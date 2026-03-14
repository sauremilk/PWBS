output "api_url" { value = "https://${aws_lb.api.dns_name}" }
output "cluster_name" { value = aws_ecs_cluster.main.name }
output "alb_dns_name" { value = aws_lb.api.dns_name }
output "alb_zone_id" { value = aws_lb.api.zone_id }
output "api_security_group_id" { value = aws_security_group.api.id }
