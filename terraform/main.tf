terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "DB-Health-Monitor"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Course      = "SI-783-Base-de-Datos-II"
      Group       = "Group-3"
    }
  }
}

# -----------------------------------------------------------------------------
# 1. RED VIRTUAL (VPC & SUBNETS)
# -----------------------------------------------------------------------------

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc-${var.environment}"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw-${var.environment}"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# -----------------------------------------------------------------------------
# 2. GRUPO DE SEGURIDAD (FIREWALL / SECURITY GROUP)
# -----------------------------------------------------------------------------

resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-sg-${var.environment}"
  description = "Reglas de seguridad para DB Health Monitor (HTTP, App 8080, SSH)"
  vpc_id      = aws_vpc.main.id

  # Acceso web directo a la aplicación
  ingress {
    description = "Puerto de la aplicacion DB Health Monitor"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Acceso HTTP estandar
  ingress {
    description = "HTTP estandar"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Acceso HTTPS seguro
  ingress {
    description = "HTTPS seguro"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Acceso SSH administrativo
  ingress {
    description = "SSH para administracion"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Salida libre a internet para descargas y telemetria
  egress {
    description = "Trafico saliente ilimitado"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# -----------------------------------------------------------------------------
# 3. GENERACION AUTOMATICA DE SECRETOS DE SEGURIDAD
# -----------------------------------------------------------------------------

resource "random_password" "postgres_password" {
  length  = 24
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

# Clave Fernet valida de 32 bytes en base64
resource "random_id" "fernet_key" {
  byte_length = 32
}

# -----------------------------------------------------------------------------
# 4. AMI Y SERVIDOR EC2 CON CLOUD-INIT / DOCKER
# -----------------------------------------------------------------------------

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "db_health_server" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  associate_public_ip_address = true
  key_name                    = var.key_name != "" ? var.key_name : null

  root_block_device {
    volume_size           = var.disk_size_gb
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
    tags = {
      Name = "${var.project_name}-root-disk"
    }
  }

  user_data = <<-EOF
              #!/bin/bash
              set -e

              # 1. Actualizacion de paquetes del sistema
              apt-get update -y
              apt-get install -y ca-certificates curl gnupg lsb-release git

              # 2. Instalacion oficial de Docker y Docker Compose Plugin
              install -m 0755 -d /etc/apt/keyrings
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
              chmod a+r /etc/apt/keyrings/docker.gpg

              echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

              apt-get update -y
              apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
              systemctl enable docker
              systemctl start docker

              # 3. Descarga del repositorio del proyecto
              mkdir -p /opt/db-health-monitor
              cd /opt/db-health-monitor
              git clone https://github.com/UPT-FAING-EPIS/si783-2026-ii-si783-2026-ii-proyecto-group-3.git .

              # 4. Creacion del archivo de variables de entorno de produccion
              cat << 'ENVFILE' > .env.deploy
              ENVIRONMENT=production
              APP_BIND_ADDRESS=0.0.0.0
              APP_PORT=${var.app_port}
              POSTGRES_DB=db_health_monitor
              POSTGRES_USER=db_health_app
              POSTGRES_PASSWORD=${random_password.postgres_password.result}
              DATABASE_URL=postgresql+psycopg://db_health_app:${random_password.postgres_password.result}@postgres:5432/db_health_monitor
              JWT_SECRET_KEY=${random_password.jwt_secret.result}
              CREDENTIALS_ENCRYPTION_KEY=${random_id.fernet_key.b64_std}
              LOG_LEVEL=INFO
              ENVFILE

              # 5. Despliegue reproducible con Docker Compose
              docker compose --env-file .env.deploy up --build -d
              EOF

  tags = {
    Name = "${var.project_name}-server-${var.environment}"
  }
}
