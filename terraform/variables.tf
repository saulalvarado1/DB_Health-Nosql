variable "aws_region" {
  description = "Region de AWS donde se desplegara la infraestructura"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Entorno de despliegue (production, staging, dev)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Nombre identificador del proyecto"
  type        = string
  default     = "db-health-monitor"
}

variable "vpc_cidr" {
  description = "Rango de red IPv4 para la VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Rango de red IPv4 para la subred publica"
  type        = string
  default     = "10.0.1.0/24"
}

variable "instance_type" {
  description = "Tipo de instancia EC2 (t3.micro para Free Tier, t3.small para produccion recomendada)"
  type        = string
  default     = "t3.small"
}

variable "disk_size_gb" {
  description = "Tamano del disco de almacenamiento gp3 en GB"
  type        = number
  default     = 20
}

variable "key_name" {
  description = "Nombre del Key Pair en AWS para acceso SSH (dejar vacio si no se requiere)"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr" {
  description = "Direccion IP o rango CIDR autorizado para conexion SSH (ej: tu IP publica x.x.x.x/32)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "app_port" {
  description = "Puerto publicado en la instancia para la aplicacion web"
  type        = number
  default     = 8080
}
