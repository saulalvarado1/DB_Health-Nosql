# Portal de Documentación Técnica — DB Health Monitor
> **Plataforma de Observabilidad Proactiva para MongoDB y Redis (v1.0)**  
> **Universidad Privada de Tacna (UPT)** — Facultad de Ingeniería (EPIS)  
> **Asignatura:** SI-783 Base de Datos II · **Grupo:** Grupo 3  

---

## 🚀 Bienvenido a la Documentación Oficial

Este portal centraliza las especificaciones de arquitectura, el modelo de datos relacional, el catálogo exhaustivo de telemetría y los informes de auditoría del sistema **DB Health Monitor**.

### 📌 Acceso Rápido por Secciones

* 🗄️ **[Modelo de Datos Relacional](data-model.md):**  
  Estructura de tablas en PostgreSQL normalizada en 3FN, claves foráneas, restricciones de integridad y modelo de muestras históricas.

* 📊 **[Catálogo de Métricas NoSQL](metric-catalog.md):**  
  Detalle técnico de los **47 indicadores** monitoreados en tiempo real (20 métricas de MongoDB y 27 de Redis).

* ⚙️ **[Requisitos No Funcionales](non-functional-requirements.md):**  
  Criterios de seguridad (cifrado AES-128 Fernet, Argon2), rendimiento, aislamiento multi-tenant y disponibilidad.

---

## 🔍 Informes de Auditoría de Calidad V1

El sistema fue sometido a ciclos rigurosos de verificación con pruebas de integración y servicios reales:

1. **[Auditoría del Backend](backend-v1-audit.md):** Validación de FastAPI, SQLAlchemy 2.0, concurrencia de workers y suite de pytest (55+ pruebas).
2. **[Auditoría del Frontend](frontend-v1-audit.md):** Pruebas de componentes React 19, Vitest, contratos de API y diseño accesible.
3. **[Auditoría de Despliegue](deployment-audit.md):** Empaquetado en contenedores Docker non-root, aislamiento de redes y túneles en producción.
4. **[Auditoría de Pruebas E2E](e2e-audit.md):** Recorrido completo automatizado de extremo a extremo con servicios reales efímeros.

---

> Utiliza el **menú de navegación de la izquierda** o el **buscador interactivo** superior para consultar cualquier sección.
