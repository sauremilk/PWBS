# PWBS  Terraform Outputs

output "api_url" {
  description = "URL des Backend-API-Service"
  value       = module.ecs.api_url
}

output "database_endpoint" {
  description = "PostgreSQL RDS Endpoint"
  value       = module.rds.endpoint
}

output "weaviate_private_ip" {
  description = "Private IP der Weaviate-Instanz"
  value       = module.ec2_weaviate.private_ip
}

output "neo4j_private_ip" {
  description = "Private IP der Neo4j-Instanz"
  value       = module.ec2_neo4j.private_ip
}

output "redis_endpoint" {
  description = "ElastiCache Redis Endpoint"
  value       = module.elasticache.endpoint
}
