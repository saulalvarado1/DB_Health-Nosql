# Infraestructura como Código (IaC) con Terraform
## DB Health Monitor — Despliegue Automatizado en AWS

Este directorio contiene la definición completa de infraestructura como código para desplegar la plataforma **DB Health Monitor** en Amazon Web Services (AWS) utilizando **Terraform**.

---

## 1. Arquitectura Aprovisionada

El código de Terraform (`main.tf`) aprovisiona de forma automatizada:

* **VPC dedicada** (`10.0.0.0/16`) con soporte DNS.
* **Subred pública** (`10.0.1.0/24`) con Internet Gateway y tabla de rutas.
* **Security Group** con reglas estrictas de firewall:
  * Puerto `8080` (Acceso a la interfaz web de DB Health Monitor).
  * Puertos `80` (HTTP) y `443` (HTTPS).
  * Puerto `22` (SSH restringido a tu IP).
* **Instancia EC2** con Ubuntu 24.04 LTS y disco SSD gp3 de 20 GB.
* **Aprovisionamiento automatizado (Cloud-Init / User Data):**
  * Instala Docker Engine y Docker Compose Plugin.
  * Clona el repositorio del proyecto.
  * Genera contraseñas criptográficas seguras y claves Fernet mediante generadores aleatorios de Terraform (`random_password` y `random_id`).
  * Construye y levanta los contenedores de PostgreSQL 16, Backend FastAPI, Worker y Frontend React.

---

## 2. Requisitos Previos

1. Tener instalado [Terraform](https://www.terraform.io/downloads.html) (versión `>= 1.5.0`).
2. Tener configuradas las credenciales de AWS en tu terminal:
   ```bash
   aws configure
   ```
   *(Requiere tu `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`).*

---

## 3. Guía de Ejecución Paso a Paso

### Paso 1: Configurar variables
Copia el archivo de ejemplo de variables:
```bash
cp terraform.tfvars.example terraform.tfvars
```
Edita `terraform.tfvars` si deseas cambiar la región de AWS o el tipo de instancia (por defecto usa `us-east-1` y `t3.small`).

### Paso 2: Inicializar Terraform
Descarga los proveedores necesarios (`hashicorp/aws`, `hashicorp/random`):
```bash
terraform init
```

### Paso 3: Validar y planificar
Verifica la sintaxis y visualiza los recursos que se van a crear:
```bash
terraform validate
terraform plan
```

### Paso 4: Aprovisionar la infraestructura
Aplica los cambios en tu cuenta de AWS:
```bash
terraform apply
```
*(Escribe `yes` cuando lo solicite).*

Al terminar, Terraform imprimirá los outputs con la dirección IP pública y la URL para abrir el sistema:
```text
Outputs:
application_url    = "http://54.208.12.34:8080"
instance_public_ip = "54.208.12.34"
```

### Paso 5: Destruir la infraestructura (Limpieza de costos)
Cuando termines las pruebas o la evaluación docente, destruye todos los recursos para no generar costos:
```bash
terraform destroy
```

---

## 4. Análisis de Costos

Para la justificación económica exigida por la rúbrica del curso, consulta el documento adjunto:
📄 [**COSTOS_ESTIMACION.md**](./COSTOS_ESTIMACION.md)
