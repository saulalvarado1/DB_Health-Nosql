<center>

![logo-upt](./media/logo-upt.png)

**UNIVERSIDAD PRIVADA DE TACNA**  
**FACULTAD DE INGENIERÍA**  
**Escuela Profesional de Ingeniería de Sistemas**  

# **INFORME FINAL DEL PROYECTO (FD05)**
## **DB Health Monitor: Plataforma Multi-Inquilino de Observabilidad y Diagnóstico de Salud para Bases de Datos NoSQL (MongoDB y Redis)**

**Curso:** SI-783 Base de Datos II (2026-II)  
**Docente:** Mag. Ing. Patrick Cuadros Quiroga  
**Grupo:** Grupo 3  
**Integrantes:**  
- Alvarado Mamani, Saúl (2021070014)  

**Tacna – Perú**  
**2026**

</center>

---

## Control de Versiones

| Versión | Hecha por | Revisada por | Aprobada por | Fecha | Motivo |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1.0 | Grupo 3 | Docente | Docente | 18/11/2026 | Versión Final Completa para Evaluación |

---

# Índice General

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Objetivos del Proyecto](#2-objetivos-del-proyecto)
3. [Arquitectura del Sistema y Tecnologías](#3-arquitectura-del-sistema-y-tecnologías)
4. [Modelo de Datos y Persistencia Relacional](#4-modelo-de-datos-y-persistencia-relacional)
5. [Cumplimiento de Requisitos No Funcionales](#5-cumplimiento-de-requisitos-no-funcionales)
   - 5.1 Sesiones y Seguridad
   - 5.2 Historiales y Auditoría
   - 5.3 Gestión de Caché
   - 5.4 Logging Estructurado
   - 5.5 Telemetría y Workers Concurrentes
6. [Reto de Integraciones Externas](#6-reto-de-integraciones-externas)
   - 6.1 Alertamiento Móvil Bidireccional (Telegram Bot API)
   - 6.2 Gestión Automatizada de Incidentes (GitHub Issues API)
   - 6.3 Integración con IDE (Extensión nativa de VS Code y Agent Skill)
7. [Infraestructura y Despliegue Automatizado](#7-infraestructura-y-despliegue-automatizado)
8. [Verificación de Calidad y Pruebas](#8-verificación-de-calidad-y-pruebas)
9. [Conclusiones y Recomendaciones](#9-conclusiones-y-recomendaciones)

---

## 1. Resumen Ejecutivo

**DB Health Monitor** es una plataforma moderna de ingeniería de software y observabilidad proactiva diseñada para supervisar, diagnosticar y alertar sobre el estado de salud, rendimiento y disponibilidad de motores de bases de datos NoSQL y en memoria (**MongoDB y Redis**).

A diferencia de las herramientas tradicionales que se limitan a mostrar gráficos pasivos, DB Health Monitor implementa un **motor de diagnóstico determinista** que normaliza las métricas operativas (latencia de red, memoria residente, saturación de conexiones, operaciones por segundo, evasión de caché y estado de replicación) y calcula un **Puntaje de Salud (Health Score)** normalizado entre 0 y 100 con diagnóstico de causa raíz y recomendaciones automatizadas.

El sistema se diseñó bajo una estricta política de **Aislamiento Multi-Inquilino (Multi-Tenancy por Propiedad)** y **Seguridad Zero-Trust**, garantizando que las credenciales de bases de datos de los clientes se almacenen cifradas en reposo con algoritmos simétricos y nunca sean expuestas en logs ni interfaces públicas.

---

## 2. Objetivos del Proyecto

### 2.1 Objetivo General
Desarrollar y desplegar una plataforma robusta y automatizada de observabilidad y diagnóstico de salud para clústeres MongoDB y Redis, con persistencia relacional en PostgreSQL, capacidades de notificación móvil, integración con repositorios Git y extensión para el entorno de desarrollo Visual Studio Code.

### 2.2 Objetivos Específicos
1. Diseñar e implementar un esquema relacional normalizado en **Tercera Forma Normal (3FN)** en PostgreSQL 16 para almacenar usuarios, instancias monitoreadas, perfiles de umbrales, muestras de métricas históricas, evaluaciones de salud y alertas.
2. Desarrollar conectores especializados de solo lectura y mínimo privilegio para extraer telemetría nativa de MongoDB y Redis sin sobrecargar los servidores monitoreados.
3. Implementar un planificador concurrente con bloqueo atómico mediante `SELECT ... FOR UPDATE SKIP LOCKED` para asegurar la recolección distribuida sin duplicación de tareas.
4. Cumplir con los retos de integración externa de la asignatura:
   - Bot conversacional e interactivo de **Telegram** para alertamiento y acuse de recibo.
   - Creación desatendida y aislada de incidencias en **GitHub Issues**.
   - Extensión nativa de **Visual Studio Code** empaquetada en `.vsix` y **Agent Skill** para asistentes de IA.
5. Proveer infraestructura como código (**Terraform**), contenedores (**Docker Compose**) y despliegue continuo en la nube (**Railway**).

---

## 3. Arquitectura del Sistema y Tecnologías

El sistema sigue el patrón de **Monolito Modular con Arquitectura Hexagonal (Ports & Adapters)**:

- **Frontend:** Single Page Application (SPA) construida en **React 18** con **TypeScript 5.8** y empaquetada con **Vite**.
- **Backend API & Workers:** Construido en **Python 3.13** con **FastAPI** y **SQLAlchemy 2.0**.
- **Base de Datos del Sistema:** **PostgreSQL 16**, con control de versiones de esquema mediante migraciones **Alembic**.
- **Motores Monitoreados:** **MongoDB** (vía motor `pymongo`) y **Redis** (vía cliente `redis-py`).
- **Autenticación y Cifrado:** Hasheo de contraseñas con **Argon2id**, tokens de sesión **JWT (HS256)** y cifrado de cadenas de conexión con **AES-128 Fernet**.

```
[ Frontend: React + TypeScript ] <──(HTTPS / JWT)──> [ Backend API: FastAPI ]
                                                              │
                    ┌─────────────────────────────────────────┼────────────────────────────────────────┐
                    ▼                                         ▼                                        ▼
      [ PostgreSQL 16 (Interno) ]               [ Worker Concurrente ]                   [ Notificaciones & Integración ]
      • Usuarios y Permisos                      • Arrendamiento SKIP LOCKED              • Telegram Bot API
      • Muestras y Evaluaciones                  • Recolección MongoDB/Redis              • GitHub Issues API
      • Reglas de Umbrales                       • Evaluación Determinista                • VS Code Extension & Agent Skill
```

---

## 4. Modelo de Datos y Persistencia Relacional

El modelo de datos se encuentra estructurado en 10 tablas interrelacionadas, documentadas detalladamente en el [Diccionario de Datos](docs/data-dictionary.md):

1. `users`: Gestión de usuarios y credenciales Argon2id.
2. `database_engines`: Catálogo maestro de motores soportados (`mongodb`, `redis`).
3. `monitored_databases`: Instancias asignadas a cada usuario con parámetros de intervalos, configuración de Telegram y GitHub Issues.
4. `monitoring_schedules`: Tabla de concurrencia y arrendamiento (`lease_owner`, `lease_expires_at`).
5. `metric_definitions`: Catálogo formal de métricas (código, unidad, dirección de alarma).
6. `threshold_profiles`: Agrupaciones lógicas de reglas de advertencia y crítico.
7. `database_threshold_profiles`: Tabla de enlace entre perfiles e instancias.
8. `threshold_rules`: Reglas numéricas específicas (`warning_value`, `critical_value`).
9. `metric_samples`: Muestras de recolección append-only en el tiempo.
10. `metric_values`: Valores unitarios recolectados en cada muestra.
11. `health_assessments`: Evaluación final de salud (Score 0-100, estado y fundamentación).
12. `alerts`: Registro de incidentes con llave de deduplicación y ciclo de vida (`open`, `acknowledged`, `resolved`).

---

## 5. Cumplimiento de Requisitos No Funcionales

### 5.1 Sesiones y Seguridad
- **Autenticación:** Tokens Bearer JWT firmados con clave simétrica secreta, con expiración configurada.
- **Protección de Datos:** Las cadenas de conexión se almacenan cifradas con `connection_uri_encrypted`.
- **Aislamiento Multi-Inquilino:** Verificado con pruebas de integración (`test_tenant_isolation_integration.py`): ningún usuario puede acceder a recursos de otro.

### 5.2 Historiales y Auditoría
- Las muestras de métricas son registros inmutables históricos (*append-only*).
- El sistema permite filtrar historiales por ventanas de tiempo (`1h`, `6h`, `24h`, `7d`, `all`).
- Exportación directa de telemetría e incidentes en formatos **CSV** y **JSON**.

### 5.3 Gestión de Caché
- Soporte especializado para diagnosticar Redis: tasa de aciertos (*hit ratio*), consumo de memoria vs. límite máximo, fragmentación de memoria y políticas de evicción de claves.

### 5.4 Logging Estructurado
- Salida de logs mediante la librería nativa `logging` con niveles configurables (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Formato uniforme con timestamps en UTC y sin exposición de secretos.

### 5.5 Telemetría y Workers Concurrentes
- Algoritmo de evaluación determinista: penalizaciones ponderadas por métricas que sobrepasan umbrales configurados.
- Planificador con exclusión mutua distribuida: dos workers no pueden tomar la misma base de datos al mismo tiempo gracias a `SELECT ... FOR UPDATE SKIP LOCKED`.

---

## 6. Reto de Integraciones Externas

| Integración | Implementación | Evidencia |
|---|---|---|
| **Telegram Bot API** | Bot conversacional bidireccional (`/status`, `/alerts`, `/ping`) con botones interactivos para acuse de recibo y aislamiento multi-tenant por Chat ID. | `backend/app/services/telegram_bot.py` |
| **GitHub Issues API** | Apertura automática de tickets con telemetría completa ante alertas críticas, configurable de forma aislada por base de datos (Zero-Trust, repo propio y token PAT cifrado). | `backend/app/services/github_issues.py` |
| **Extensión de VS Code** | Extensión nativa con indicador en Status Bar, panel lateral en Activity Bar, árbol de telemetría y comandos integrados en la paleta. Empaquetada en archivo binario autoinstalable `.vsix`. | `vscode-extension/db-health-monitor-1.0.0.vsix` |
| **Agent Skill de IA** | Definición formal de contexto y capacidades para asistentes de IA (Copilot / Cursor / Antigravity) para diagnosticar bases de datos en lenguaje natural. | `.vscode/skills/dbhealth.md` |

---

## 7. Infraestructura y Despliegue Automatizado

1. **Despliegue en la Nube (Railway):**
   - **Frontend en Producción:** [https://frontend-production-07c5.up.railway.app](https://frontend-production-07c5.up.railway.app)
   - **Backend & PostgreSQL en Railway:** Despliegue automático conectado al repositorio GitHub.
2. **Infraestructura como Código (IaC):**
   - Configuración completa de Terraform en [`terraform/main.tf`](terraform/main.tf) para aprovisionamiento de VPC, subredes, grupos de seguridad, base de datos RDS PostgreSQL y generación automática de secretos.
3. **Pipelines de CI/CD (GitHub Actions):**
   - `.github/workflows/ci.yml`: Ejecución automática de pruebas de backend y frontend ante cada push/PR.
   - `.github/workflows/pages.yml`: Publicación automatizada de la documentación técnica y diagramas Mermaid en GitHub Pages.
   - `.github/workflows/backup.yml`: Automatización de copias de seguridad de la base de datos PostgreSQL.

---

## 8. Verificación de Calidad y Pruebas

| Capa | Herramienta | Pruebas Ejecutadas | Resultado |
|---|---|:---:|:---:|
| **Backend Unit & Logic** | Pytest | 64 pruebas pasadas | ✅ 100% Exitoso |
| **Backend Integración Real** | Pytest + PostgreSQL + MongoDB + Redis | 3 pruebas pasadas | ✅ 100% Exitoso |
| **Frontend Components & API** | Vitest | 25 pruebas pasadas | ✅ 100% Exitoso |
| **Frontend Compilación & Tipos** | TypeScript + Vite | `tsc -b && vite build` | ✅ 100% Exitoso |
| **Pruebas de Extremo a Extremo** | Playwright + Edge | 1 prueba de flujo completo | ✅ 100% Exitoso |

---

## 9. Conclusiones y Recomendaciones

### 9.1 Conclusiones
1. Se cumplió satisfactoriamente con la totalidad de los requerimientos funcionales y no funcionales exigidos en la asignatura SI-783 Base de Datos II.
2. La arquitectura de Monolito Modular permitió mantener una estricta separación de responsabilidades, facilitando la incorporación de nuevas capacidades (como la configuración aislada de GitHub Issues y la extensión de VS Code) sin degradar la estabilidad del núcleo.
3. El uso de PostgreSQL 16 como base de datos relacional del sistema garantiza la integridad referencial, el control transaccional estricto y la coordinación concurrente de los workers de recolección.

### 9.2 Recomendaciones
1. Para versiones futuras (V2.0), se sugiere explorar la compatibilidad con motores adicionales como Cassandra o bases de datos de grafos (Neo4j).
2. Se recomienda mantener la política de rotación periódica de las claves maestras de cifrado (`CREDENTIALS_ENCRYPTION_KEY`) mediante pipelines programados de mantenimiento.
