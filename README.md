# DB Health Monitor (v1.0)
### Plataforma de Observabilidad Proactiva y Diagnóstico de Salud para Bases de Datos NoSQL y en Memoria

[![CI Status](https://img.shields.io/badge/CI-GitHub_Actions_Passing-2ea44f?style=for-the-badge&logo=githubactions&logoColor=white)](#pipeline-de-cicd-y-automatización)
[![Release](https://img.shields.io/badge/Release-v1.0.0-0284c7?style=for-the-badge&logo=github&logoColor=white)](#módulos-del-sistema)
[![Database](https://img.shields.io/badge/PostgreSQL-16_(3FN)-336791?style=for-the-badge&logo=postgresql&logoColor=white)](#modelo-de-datos-relacional-en-3fn)
[![Backend](https://img.shields.io/badge/FastAPI-Python_3.13-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#arquitectura-de-software)
[![Frontend](https://img.shields.io/badge/React_19-TypeScript-61dafb?style=for-the-badge&logo=react&logoColor=black)](#arquitectura-de-software)
[![Docker](https://img.shields.io/badge/Docker-Compose_Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)](#despliegue-reproducible)

---

## 🏛️ Información Institucional y Equipo de Proyecto

* **Institución:** Universidad Privada de Tacna (UPT)
* **Facultad:** Facultad de Ingeniería (FAING)
* **Escuela:** Escuela Profesional de Ingeniería de Sistemas (EPIS)
* **Asignatura:** SI-783 Base de Datos II (2026-II)
* **Equipo de Desarrollo:** **Grupo 3**
* **Repositorio Oficial:** [`UPT-FAING-EPIS/si783-2026-ii-si783-2026-ii-proyecto-group-3`](https://github.com/UPT-FAING-EPIS/si783-2026-ii-si783-2026-ii-proyecto-group-3)
* **Despliegue en Producción (Demo):** [frontend-production-07c5.up.railway.app](https://frontend-production-07c5.up.railway.app)
* **Portal de Documentación Técnica:** [GitHub Pages Documentation](https://upt-faing-epis.github.io/si783-2026-ii-si783-2026-ii-proyecto-group-3/)

---

## 💡 ¿Qué es DB Health Monitor?

**DB Health Monitor** es una plataforma centralizada y multiusuario de observabilidad para **MongoDB** y **Redis**. Permite a DBAs, ingenieros DevOps y líderes técnicos supervisar la salud integral de sus bases de datos en tiempo real mediante un enfoque no invasivo:

1. **Arquitectura 100% Agentless (Sin Agentes):** No requiere instalar software residente en los servidores clientes. Extrae telemetría mediante conexiones remotas estándar y comandos nativos ligeros de solo lectura (`serverStatus`, `INFO`).
2. **Score de Salud Determinista (0 a 100):** Consolida 47 métricas técnicas en un indicador de salud comprensible en 3 segundos (`Saludable: 80-100`, `Advertencia: 50-79`, `Crítico: 0-49`), con explicaciones legibles de causas de penalización.
3. **Alertamiento Proactivo vía Telegram Bot:** Envía notificaciones instantáneas push a los dispositivos móviles de guardia ante caídas de conexión o violación de umbrales, con control inteligente de duplicados.
4. **Seguridad Zero-Trust:** Cifrado simétrico en reposo con **AES-128 Fernet** para cadenas de conexión, hasheo de contraseñas de usuarios con **Argon2id** y autenticación stateless con **JWT**.

---

## 🏗️ Arquitectura de Software y Diagramas de Ingeniería

El sistema está estructurado como un **Monolito Modular** de alto rendimiento, aplicando los principios de la Arquitectura Hexagonal (Puertos y Adaptadores) y el Patrón Repositorio.

### 1. Diagrama de Componentes (C4 Nivel 2)

```mermaid
graph TD
    User["👤 Usuario / DBA"] -->|HTTPS / WSS| Nginx["🌐 Nginx Web Proxy (Puerto 8080)"]
    Nginx -->|Sirve SPA estática| ReactApp["⚛️ React 19 + TypeScript SPA"]
    Nginx -->|Redirige /api/v1| FastAPI["⚡ Backend API (FastAPI / Python 3.13)"]
    
    FastAPI -->|Autenticación & Consultas| PostgreSQL[("🐘 PostgreSQL 16 (Plataforma 3FN)")]
    
    subgraph "Worker de Monitoreo Autónomo"
        Worker["🔄 Background Worker (Python 3.13)"]
        Worker -->|Reserva concurrente: SKIP LOCKED| PostgreSQL
        Worker -->|Despacha alertas| TelegramBot["📱 Telegram Bot API (Push Notifications)"]
    end
    
    subgraph "Infraestructura Monitoreada (Agentless)"
        Worker -->|db.command('serverStatus')| MongoDB[("🍃 MongoDB Clúster / Instancia")]
        Worker -->|INFO / PING de solo lectura| Redis[("⚡ Redis Instancia / Caché")]
    end

    classDef primary fill:#0284c7,stroke:#0369a1,color:#fff;
    classDef secondary fill:#0f172a,stroke:#334155,color:#fff;
    classDef highlight fill:#059669,stroke:#047857,color:#fff;
    class ReactApp,FastAPI primary;
    class PostgreSQL,Worker secondary;
    class MongoDB,Redis,TelegramBot highlight;
```

---

### 2. Diagrama de Despliegue (Deployment Diagram)

```mermaid
graph TB
    subgraph "Cliente"
        Browser["💻 Navegador Web / Dispositivo Móvil"]
    end

    subgraph "Host de Despliegue (Docker Host / AWS EC2 / Railway)"
        subgraph "Zona Pública (DMZ)"
            Nginx["🌐 Nginx Web Proxy\n(:8080 HTTP / :443 TLS)"]
        end

        subgraph "Red Interna Aislada (Docker bridge network)"
            ReactStatic["📦 Frontend SPA Assets\n(React 19 / HTML5 / JS)"]
            FastAPIApp["⚡ Backend REST API\n(Python 3.13 / Uvicorn :8000)"]
            WorkerProcess["🔄 Background Worker\n(Daemon Python 3.13)"]
            PostgreSQLDB[("🐘 PostgreSQL 16 Service\n(:5432 - Persistencia 3FN)")]
            StorageVolume[("💾 Docker Volume\n/var/lib/postgresql/data")]
        end
    end

    subgraph "Servicios Externos & Nube"
        TelegramAPI["📱 Telegram Bot API\n(HTTPS :443 Push Alerts)"]
        RemoteMongo[("🍃 Instancia Remota MongoDB\n(:27017 Read-Only Agentless)")]
        RemoteRedis[("⚡ Instancia Remota Redis\n(:6379 Read-Only Agentless)")]
    end

    Browser -->|HTTP/HTTPS :8080| Nginx
    Nginx -->|Sirve estáticos /| ReactStatic
    Nginx -->|Reverse Proxy /api/v1| FastAPIApp
    FastAPIApp -->|TCP :5432 SQLAlchemy| PostgreSQLDB
    WorkerProcess -->|TCP :5432 SKIP LOCKED| PostgreSQLDB
    PostgreSQLDB --- StorageVolume
    WorkerProcess -->|HTTPS :443| TelegramAPI
    WorkerProcess -->|TCP :27017 serverStatus| RemoteMongo
    WorkerProcess -->|TCP :6379 INFO / PING| RemoteRedis
```

---

### 3. Diagrama de Clases (Class Diagram)

```mermaid
classDiagram
    class User {
        +UUID id
        +string email
        +string password_hash
        +boolean is_active
        +datetime created_at
        +datetime updated_at
    }

    class MonitoredDatabase {
        +UUID id
        +UUID owner_id
        +string engine_id
        +string name
        +string connection_string_encrypted
        +boolean is_active
    }

    class HealthAssessment {
        +UUID id
        +UUID metric_sample_id
        +int score
        +string status
        +string summary
    }

    class ThresholdRule {
        +UUID id
        +UUID profile_id
        +UUID metric_definition_id
        +string operator
        +float warning_threshold
        +float critical_threshold
    }

    class AuthenticationService {
        -_session: Session
        -_users: UserRepository
        +register(command: RegisterUserCommand) User
        +authenticate(email: str, password: str) User
    }

    class HealthScoreEngine {
        +evaluate(metrics: dict, rules: list) HealthAssessmentResult
        -calculate_penalties(metrics: dict, rules: list) int
    }

    class BaseConnector {
        <<interface>>
        +collect_metrics()* dict
        +ping()* bool
    }

    class MongoDBConnector {
        -_connection_string: str
        +collect_metrics() dict
        +ping() bool
    }

    class RedisConnector {
        -_connection_string: str
        +collect_metrics() dict
        +ping() bool
    }

    BaseConnector <|.. MongoDBConnector : implements
    BaseConnector <|.. RedisConnector : implements
    User "1" --> "*" MonitoredDatabase : owns
    MonitoredDatabase "1" --> "*" HealthAssessment : generates
    ThresholdRule "*" --> "1" MonitoredDatabase : applies_to
    AuthenticationService ..> User : manages
    HealthScoreEngine ..> HealthAssessment : produces
```

---

### 4. Diagrama de Entidad-Relación (ERD 3FN)

PostgreSQL 16 almacena la configuración de la plataforma, usuarios, catálogos, historial de métricas y alertas. Cumple estrictamente la **Tercera Forma Normal (3FN)**:

```mermaid
erDiagram
    users ||--o{ monitored_databases : "posee (1:N)"
    database_engines ||--o{ monitored_databases : "tipifica (1:N)"
    monitored_databases ||--|| monitoring_schedules : "programa (1:1)"
    monitored_databases ||--o{ database_threshold_profiles : "asigna (1:1)"
    threshold_profiles ||--o{ database_threshold_profiles : "asocia (1:N)"
    threshold_profiles ||--o{ threshold_rules : "contiene (1:N)"
    metric_definitions ||--o{ threshold_rules : "define regla (1:N)"
    database_engines ||--o{ metric_definitions : "cataloga (1:N)"
    monitored_databases ||--o{ metric_samples : "recolecta (1:N)"
    metric_samples ||--o{ metric_values : "contiene valores (1:N)"
    metric_definitions ||--o{ metric_values : "califica metrica (1:N)"
    metric_samples ||--|| health_assessments : "evalua salud (1:1)"
    monitored_databases ||--o{ alerts : "genera (1:N)"
    metric_samples ||--o{ alerts : "asocia incidente (1:N)"
    threshold_rules ||--o{ alerts : "dispara (1:N)"
```

---

### 5. Diccionario de Datos Completo de PostgreSQL

Para la especificación exhaustiva columna por columna, tipos de datos SQL, restricciones de integridad e índices:  
📖 **[Diccionario de Datos Completo (12 Tablas 3FN)](docs/data-dictionary.md)**  
📖 **[Especificación Técnica de Clases, Métodos y Propiedades](docs/technical-specification.md)**

---

## 📦 Módulos del Sistema y Entregables de la Rúbrica

| Módulo / Directorio | Descripción y Propósito | Estado / Rúbrica |
| :--- | :--- | :---: |
| [`backend/`](backend/) | API REST en FastAPI, worker de fondo y modelos de dominio. | ✅ Verificado (55+ tests) |
| [`frontend/`](frontend/) | Interfaz gráfica SPA en React 19, TypeScript, Vitest y gráficos SVG. | ✅ Verificado |
| [`terraform/`](terraform/) | Infraestructura como Código (IaC) en AWS y [Estimación de Costos](terraform/COSTOS_ESTIMACION.md). | ✅ Aprovisionable |
| [`liquibase/`](liquibase/) | Control de versiones de la BD con changelogs XML y [Reporte Técnico](liquibase/report/REPORTE_MIGRACIONES_LIQUIBASE.md). | ✅ Versionado |
| [`backups/`](backups/) | Scripts automatizados de backup (`pg_dump`), verificación SHA-256 y [Plan DRP](backups/report/REPORTE_BACKUPS_Y_RECUPERACION.md). | ✅ Probado (<5s RTO) |
| [`.github/workflows/`](.github/workflows/) | Pipelines de CI (pruebas/linters), CD de Release y despliegue a GitHub Pages. | ✅ Automatizado |
| [`docs/`](docs/) | Documentación técnica, modelo de datos, catálogo y auditorías para GitHub Pages. | ✅ Publicable |
| [`vscode-extension/`](vscode-extension/) | Extensión oficial de Visual Studio Code y [Agent Skill](.vscode/skills/dbhealth.md). | ✅ Cumple Reto |

---

## 🎯 Reto de Integraciones Externas (3 Herramientas + VS Code)

Para dar cumplimiento estricto y sobresaliente al **Reto de Integraciones** de la asignatura, el sistema implementa la tríada de integración continua:

1. **📱 Herramienta 1 — Telegram Bot API (Alertamiento Móvil Bidireccional):**
   * Despacho proactivo de alertas con severidad (`CRITICAL`, `WARNING`, `RECOVERY`) y deduplicación inteligente.
   * Botones interactivos en línea (*Inline Keyboards*) para **Reconocer Incidentes** desde el celular y enlace directo a la web.
   * Asistente conversacional con comandos en vivo: `/status`, `/alerts`, `/ping` y `/help`.
2. **🐙 Herramienta 2 — GitHub Issues API (Gestión Automática de Incidentes):**
   * Creación desatendida de tickets/issues en el repositorio GitHub oficial cuando una base de datos cae a estado crítico.
   * Carga de telemetría, causa raíz, Score 0/100 y etiquetado automático (`critical-alert`, `bug`).
3. **💻 Herramienta 3 & Reto VS Code — Extensión de Visual Studio Code & Agent Skill:**
   * **Extensión nativa (`vscode-extension/`):** Indicador de salud en la barra de estado (`Status Bar`), explorador lateral en el `Activity Bar` con árbol de métricas (latencia, memoria, conexiones) y paleta de comandos.
   * **Agent Skill (`.vscode/skills/dbhealth.md`):** Definición de contexto para agentes de IA (Copilot / Cursor / Antigravity) para diagnosticar bases de datos en lenguaje natural.

---

---

## 🚀 Despliegue Rápido y Ejecución

### 1. Despliegue Local con Docker Compose (Recomendado)
Requiere tener instalados Docker y Docker Compose:

```powershell
# 1. Generar variables de entorno seguras
.\deploy\generate-env.ps1

# 2. Levantar toda la plataforma en contenedores aislados
docker compose --env-file .env.deploy up --build -d

# 3. Comprobar estado de los servicios
docker compose --env-file .env.deploy ps
```
La aplicación queda disponible inmediatamente en: **`http://localhost:8080`**

Para detener los contenedores conservando los datos de PostgreSQL:
```powershell
docker compose --env-file .env.deploy down
```

---

### 2. Infraestructura en la Nube con Terraform (AWS)
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```
*(Al finalizar, Terraform devuelve la URL e IP pública de la instancia aprovisionada).*

---

### 3. Migraciones de Base de Datos con Liquibase
Ejecución sin necesidad de instalar Java (utilizando el contenedor oficial de Liquibase):
```powershell
# Aplicar todos los changesets pendientes:
.\liquibase\run-liquibase.ps1 -Action update

# Ver historial de cambios aplicados:
.\liquibase\run-liquibase.ps1 -Action history
```

---

### 4. Respaldo y Restauración de Base de Datos (Backups & DRP)
```powershell
# Generar un respaldo inmediato con rotación automática de 7 días:
.\backups\scripts\backup.ps1

# Restaurar con validación criptográfica previa SHA-256:
.\backups\scripts\restore.ps1
```

---

## 🧪 Pruebas Automatizadas y Calidad de Código

El proyecto cuenta con suites de pruebas unitarias, de integración y extremo a extremo:

* **Pruebas de Backend (Pytest):**
  ```powershell
  cd backend
  pytest -m "not real_services" -v
  ```
* **Linter de Backend (Ruff):**
  ```powershell
  cd backend
  ruff check .
  ```
* **Pruebas y Linter de Frontend (Vitest + ESLint):**
  ```powershell
  cd frontend
  npm run lint
  npm run test
  npm run build
  ```
* **Pruebas E2E Aisladas (Navegador real con Docker):**
  ```powershell
  .\deploy\run-e2e.ps1
  ```

---

## 📄 Informes y Documentos Oficiales del Proyecto

En la raíz del repositorio se encuentran los informes formales de ingeniería de software en formatos `.docx` y `.pdf`:

* 📑 **FD01:** Informe de Factibilidad y Viabilidad del Proyecto.
* 📑 **FD02:** Documento de Visión y Alcance.
* 📑 **FD03:** Especificación de Requerimientos de Software (SRS).
* 📑 **FD04:** Informe de Arquitectura de Software (SAD).
* 📑 **FD05:** Informe Final del Proyecto.
* 📑 **FD06:** Propuesta de Proyecto.
* 🎤 **[GUIA_EXPOSICION_PROYECTO.txt](GUIA_EXPOSICION_PROYECTO.txt):** Guion de exposición de 7 minutos, pitch de alto impacto y respuestas a las 6 preguntas más difíciles del jurado.
