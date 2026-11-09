output "instance_id" {
  description = "Identificador de la instancia EC2 creada"
  value       = aws_instance.db_health_server.id
}

output "instance_public_ip" {
  description = "Direccion IP publica del servidor en AWS"
  value       = aws_instance.db_health_server.public_ip
}

output "instance_public_dns" {
  description = "Nombre DNS publico proporcionado por AWS"
  value       = aws_instance.db_health_server.public_dns
}

output "application_url" {
  description = "URL directa para acceder a DB Health Monitor en el navegador"
  value       = "http://${aws_instance.db_health_server.public_ip}:${var.app_port}"
}

output "ssh_command" {
  description = "Comando rapido para conectarse por SSH al servidor (si se configuro key_name)"
  value       = var.key_name != "" ? "ssh -i ${var.key_name}.pem ubuntu@${aws_instance.db_health_server.public_ip}" : "SSH no configurado con key pair"
}
