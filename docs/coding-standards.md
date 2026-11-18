# Estándar de Programación y Guía de Estilo de Código
## DB Health Monitor (v1.0)
**Institución:** Universidad Privada de Tacna (UPT) — Facultad de Ingeniería (EPIS)  
**Curso:** SI-783 Base de Datos II  
**Grupo:** Grupo 3  
**Fecha:** Noviembre 2026  

---

## 1. Propósito y Alcance

Este documento establece las directrices, convenciones y estándares de codificación obligatorios para el desarrollo, mantenimiento y evolución del sistema **DB Health Monitor**. Aplica a todos los componentes del repositorio: backend (Python/FastAPI), frontend (React/TypeScript), base de datos relacional (PostgreSQL/Alembic), scripts de automatización e infraestructura como código.

---

## 2. Principios de Arquitectura y Diseño

1. **Monolito Modular:** El sistema se organiza como un monolito desacoplado en capas lógicas bien delimitadas:
   - **Rutas (`api/routes`):** Entrada HTTP, validación de esquemas y mapeo de excepciones de dominio a códigos de estado HTTP.
   - **Servicios (`services`):** Lógica de negocio pura, cálculo determinista de salud y coordinación de notificaciones.
   - **Repositorios (`infrastructure/repositories`):** Acceso y persistencia en PostgreSQL sin exponer entidades de infraestructura al exterior.
   - **Conectores (`infrastructure/connectors`):** Adaptadores específicos de motor (MongoDB, Redis) que recolectan métricas y las normalizan.
2. **Aislamiento Multi-Inquilino (Multi-Tenancy por Propiedad):**
   - Cada consulta y mutación debe filtrar rigurosamente por el identificador del propietario (`owner_id == current_user.id`).
3. **Cero Secretos en Claro (Zero-Trust Security):**
   - Las contraseñas de usuarios deben hashearse obligatoriamente con **Argon2id**.
   - Las credenciales y URIs de conexión a bases de datos monitoreadas deben almacenarse cifradas con **AES-128 Fernet** (`CredentialsCipher`).
   - Ningún secreto debe imprimirse en logs, pruebas, volcados de error ni respuestas JSON públicas de la API.
4. **Mínimo Privilegio:**
   - La plataforma utiliza cuentas de solo lectura para sondear MongoDB y Redis. El monitor nunca debe modificar datos de usuario.

---

## 3. Estándar de Programación para el Backend (Python 3.13 / FastAPI)

### 3.1 Guía de Estilo y Linters
- **Guía Base:** Cumplimiento estricto de [PEP 8](https://peps.python.org/pep-0008/).
- **Linter y Formateador Oficial:** [Ruff](https://astral.sh/ruff) configurado en `backend/pyproject.toml`.
  - Longitud máxima de línea: **100 caracteres**.
  - Sangría: 4 espacios (prohibido el uso de tabuladores).
  - Codificación de archivos: UTF-8 sin BOM con saltos de línea LF.
  - Reglas activas: `E` (pycodestyle), `F` (Pyflakes), `I` (isort para orden de imports), `B` (flake8-bugbear), `UP` (pyupgrade).

### 3.2 Tipado Estático y Modelos
- Todo código debe usar **Type Hints** completos (Python 3.10+ syntax: `int | None`, `list[str]`, `dict[str, Any]`).
- Los contratos de API se definen mediante modelos **Pydantic v2** (`BaseModel`).
- Los secretos en requests se encapsulan con `SecretStr` para evitar fugas automáticas en representaciones `__repr__`.
- Uso de `from __future__ import annotations` en archivos de servicio.

### 3.3 Manejo de Errores y Excepciones
- Prohibido capturar excepciones genéricas con `except Exception: pass` silencioso sin logging contextual.
- Las capas internas deben emitir excepciones del dominio (`DomainError`):
  - `AuthenticationError` (mapeado a HTTP 401).
  - `ResourceNotFoundError` (mapeado a HTTP 404).
  - `ResourceConflictError` (mapeado a HTTP 409).
  - `ConfigurationError` (mapeado a HTTP 400).
  - `ServiceUnavailableError` (mapeado a HTTP 503).

### 3.4 Concurrencia y Bases de Datos
- Las operaciones con base de datos deben realizarse mediante sesiones de **SQLAlchemy 2.0** con mapeo declarativo tipado (`Mapped[...]` y `mapped_column(...)`).
- Las tareas en segundo plano concurrentes deben coordinarse mediante bloqueos atómicos pesimistas con `SELECT ... FOR UPDATE SKIP LOCKED` para garantizar que múltiples instancias del worker no procesen la misma tarea duplicada.

---

## 4. Estándar de Programación para el Frontend (React 18 / TypeScript / Vite)

### 4.1 Tipado Estricto
- TypeScript configurado con `"strict": true`.
- **Prohibido el uso de `any`:** Todos los datos que ingresan desde la API deben tener contratos tipados en `frontend/src/api/contracts.ts`.
- Nombres de interfaces y tipos en `PascalCase` (ej. `MonitoredDatabase`, `ThresholdProfile`).

### 4.2 Arquitectura de Componentes
- Componentes funcionales puros basados en Hooks (`useState`, `useEffect`, `useCallback`, `useMemo`).
- Nomenclatura de archivos de componentes: `PascalCase.tsx` (ej. `DatabaseDetailPage.tsx`).
- Nomenclatura de utilidades y hooks: `camelCase.ts` / `useHook.ts` (ej. `useAutoRefresh.ts`, `http-client.ts`).
- Separación de responsabilidades: los componentes de vista no invocan `fetch` directamente, sino a través de los clientes organizados en `frontend/src/api/resources.ts`.

### 4.3 Experiencia de Usuario y Manejo Asíncrono
- Todo botón de acción asíncrona debe reflejar estado de carga (`busy`) y desactivarse durante la petición para evitar envíos dobles.
- Manejo visual de errores (`ErrorNotice`) y confirmaciones de éxito (`SuccessNotice`).
- Limpieza segura de recursos (ej. liberación diferida de ObjectURLs en descargas CSV/JSON).

---

## 5. Estándar de Base de Datos (PostgreSQL 16)

1. **Normalización:** Esquema diseñado rigurosamente en **Tercera Forma Normal (3FN)**.
2. **Convención de Nomenclatura:**
   - Tablas en plural y en minúsculas con `snake_case` (ej. `monitored_databases`, `metric_samples`).
   - Columnas en singular con `snake_case` (ej. `engine_id`, `created_at`).
   - Claves primarias con nombre `id` de tipo `UUID`.
   - Claves foráneas con sufijo `_id` (ej. `owner_id`, `sample_id`).
   - Restricciones únicas con prefijo `uq_` (ej. `uq_monitored_database_owner_engine_name`).
   - Índices secundarios con prefijo `ix_` (ej. `ix_monitored_databases_owner_id`).
3. **Control de Esquema con Migraciones:**
   - Todo cambio de base de datos se implementa mediante archivos de migración versionados en **Alembic** (`backend/migrations/versions/`).
   - Queda estrictamente prohibido alterar tablas directamente en producción sin su correspondiente script de migración y reversión (`upgrade()` / `downgrade()`).

---

## 6. Estándares de Control de Versiones (Git) y CI/CD

### 6.1 Formato de Mensajes de Commit (Conventional Commits)
Los commits deben seguir la convención estructurada:
- `feat(...)`: Nueva funcionalidad o capacidad para el usuario.
- `fix(...)`: Corrección de un defecto o fallo detectado.
- `test(...)`: Incorporación o ajuste de pruebas unitarias o de integración.
- `docs(...)`: Documentación técnica, manuales o diagramas.
- `refactor(...)`: Reestructuración de código sin alterar su comportamiento externo.
- `chore(...)`: Tareas de mantenimiento, dependencias o empaquetado.

### 6.2 Higiene del Repositorio
- Prohibido commitear archivos de entorno (`.env`), entornos virtuales (`.venv`), cachés de pruebas (`.pytest_cache`, `__pycache__`) o credenciales reales.
- Las ramas de trabajo se integran a `main` tras superar la suite de pruebas unitarias y de análisis estático.

---

## 7. Verificación de Calidad

Antes de cada entrega o release, se debe verificar el cumplimiento automático de los estándares ejecutando:

```bash
# 1. Verificación de Backend (Linter y Pruebas)
cd backend
ruff check .
pytest tests/

# 2. Verificación de Frontend (TypeScript y Pruebas Unitarias)
cd ../frontend
npm test
npm run build
```
