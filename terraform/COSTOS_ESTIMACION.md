# Estimación y Análisis de Costos de Infraestructura en la Nube
## DB Health Monitor (v1.0)
**Institución:** Universidad Privada de Tacna (UPT) — Facultad de Ingeniería (EPIS)  
**Curso:** SI-783 Base de Datos II / Proyecto de Sistemas  
**Grupo:** Grupo 3  
**Región de Referencia:** AWS `us-east-1` (N. Virginia)  

---

## 1. Resumen Ejecutivo de Costos

La arquitectura de **DB Health Monitor** fue diseñada deliberadamente bajo un enfoque de **alta eficiencia de recursos y bajo costo operativo (Cost-Efficiency Radical)**. Al tratarse de un **Monolito Modular** empaquetado en contenedores Docker y operar con telemetría ligera sin agentes (*agentless*), el consumo computacional es mínimo y predecible.

A continuación se presentan los tres escenarios de costos evaluados:

| Escenario de Despliegue | Perfil Computacional | Costo Estimado Mensual (USD) | Público Objetivo |
| :--- | :--- | :---: | :--- |
| **1. AWS Free Tier (Capa Gratuita)** | EC2 `t3.micro` + 20 GB gp3 | **$0.00 USD / mes** | Evaluación académica, pruebas y prototipos. |
| **2. Producción Base Recomendada** | EC2 `t3.small` + 20 GB gp3 + IPv4 | **$20.43 USD / mes** | Pequeñas y medianas empresas, startups. |
| **3. Alta Disponibilidad Gestionada** | EC2 `t3.small` + AWS RDS PostgreSQL | **$34.20 USD / mes** | Empresas con requerimientos estrictos de SLA de BD. |

---

## 2. Desglose Detallado por Escenario

### Escenario 1: Capa Gratuita (AWS Free Tier — 12 Meses)
Apto para cuentas nuevas de AWS durante el primer año:

| Componente | Capacidad / Uso | Tarifa Oficial AWS | Costo Mensual |
| :--- | :--- | :--- | :---: |
| **Cómputo (EC2)** | 1 instancia `t3.micro` (750 horas/mes) | $0.00 (Incluido en Free Tier) | $0.00 |
| **Almacenamiento (EBS)** | 20 GB gp3 (Hasta 30 GB gratis) | $0.00 (Incluido en Free Tier) | $0.00 |
| **Red (Data Transfer)** | 100 GB salientes a Internet | $0.00 (Incluido en Free Tier) | $0.00 |
| **VPC & Security Groups** | Red virtual privada básica | $0.00 (Sin costo) | $0.00 |
| **TOTAL MENSUAL** | | | **$0.00 USD** |

---

### Escenario 2: Producción Base Recomendada (AWS On-Demand)
Este es el escenario implementado en el código de **Terraform** (`terraform/main.tf`):

* **Instancia EC2 `t3.small`:** 2 vCPUs y 2.0 GiB de memoria RAM, ideal para alojar simultáneamente PostgreSQL, FastAPI Backend, Celery/Worker y el Frontend en Nginx.
  * Cálculo: `$0.0208 USD/hora × 730 horas/mes` = **$15.18 USD**
* **Almacenamiento EBS gp3 (20 GB):**
  * Cálculo: `20 GB × $0.08 USD/GB-mes` = **$1.60 USD**
  * 3,000 IOPS base y 125 MB/s de rendimiento sin costo adicional.
* **Dirección IPv4 Pública (Cargo AWS desde Febrero 2024):**
  * Cálculo: `$0.005 USD/hora × 730 horas/mes` = **$3.65 USD**
* **Transferencia de datos saliente:**
  * Estimada en ~5 GB/mes para tráfico de métricas y dashboards (los primeros 100 GB mensuales de salida de datos en AWS son gratuitos). = **$0.00 USD**

$$\text{Costo Total Mensual (Escenario 2)} = \$15.18 + \$1.60 + \$3.65 = \mathbf{\$20.43 \text{ USD / mes}}$$

---

### Escenario 3: Producción con Base de Datos Relacional Gestionada (AWS RDS)
Si la empresa prefiere delegar el mantenimiento y copias de seguridad de PostgreSQL directamente a AWS RDS:

| Componente | Detalle | Costo Mensual |
| :--- | :--- | :---: |
| **Servidor de Aplicación (EC2)** | `t3.micro` (1 vCPU, 1 GB RAM) solo para Backend + Frontend | $7.59 USD |
| **Base de Datos Gestionada (RDS)** | `db.t3.micro` PostgreSQL (Single-AZ, 20 GB almacenamiento gp3) | $17.80 USD |
| **Backups automatizados RDS** | Retención de 7 días (incluido dentro del almacenamiento asignado) | $0.00 USD |
| **Dirección IPv4 pública EC2** | 730 horas | $3.65 USD |
| **Almacenamiento EBS EC2** | 10 GB gp3 para el sistema operativo | $0.80 USD |
| **Transferencia interna VPC** | Tráfico entre EC2 y RDS en la misma zona de disponibilidad | $0.00 USD |
| **TOTAL MENSUAL** | | **$29.84 USD** |

---

## 3. Comparativa de Costos vs Soluciones Alternativas

| Solución / Plataforma | Costo Mensual Estimado | Desventajas / Comparación |
| :--- | :---: | :--- |
| **DB Health Monitor (en AWS con Terraform)** | **~$20 USD** | Infraestructura propia, 100% control de datos, sin límite de consultas. |
| **DB Health Monitor (en Railway PaaS)** | **~$5 USD** | Despliegue en contenedores gestionados sin configuración de VPC. |
| **Datadog (SaaS Comercial)** | **~$280 - $450 USD** | Cobra entre $15 y $23 por nodo/mes + cargos por métricas y retención. Invasivo y costoso. |
| **New Relic (SaaS Comercial)** | **~$150 - $300 USD** | Tarifa por usuario y por GB de telemetría ingerido. |
| **Prometheus + Grafana en EKS (Kubernetes)** | **~$95 - $140 USD** | Sobrecosto de nodo de control de Kubernetes y balanceadores de carga ALB. |

> **Conclusión Financiera:** Implementar DB Health Monitor representa un **ahorro de más del 90%** frente a contratar licencias de plataformas de observabilidad comerciales propietarias.

---

## 4. Estrategias de Optimización y FinOps (Ahorro Continuo)

Para optimizar aún más el presupuesto en entornos de producción:

1. **AWS Savings Plans / Compute Savings Plans (Compromiso a 1 o 3 años):**
   * Reduce el costo de la instancia EC2 hasta en un **37%** en comparación con la tarifa On-Demand ($9.50 USD en lugar de $15.18 USD).
2. **Apagado programado en ambientes de prueba / laboratorio:**
   * Apagar las instancias fuera del horario de oficina (de 8:00 pm a 8:00 am y fines de semana) reduce el uso a 240 horas mensuales, bajando el costo de cómputo a menos de **$5.00 USD al mes**.
3. **Optimización de snapshots de backup:**
   * Políticas de ciclo de vida en AWS S3 para mover copias de seguridad antiguas a clases de almacenamiento frío como *S3 Glacier Flexible Retrieval* ($0.0036 por GB-mes).
