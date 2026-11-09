# 🤖 DB Health Monitor — Agent Skill para Visual Studio Code

Este skill permite a los agentes de IA (como GitHub Copilot, Cursor o Antigravity) interactuar con la plataforma **DB Health Monitor** para consultar el estado de salud, métricas de rendimiento y resolver incidentes de bases de datos NoSQL directamente desde el editor de código.

---

## 🎯 Capacidades del Skill

1. **Consulta de Salud en Lenguaje Natural:**
   - *"¿Cómo está la base de datos de producción?"*
   - *"¿Hay alguna alerta crítica en Redis o MongoDB?"*
   - *"¿Cuál es la latencia actual del clúster?"*

2. **Acceso a Endpoints del Monitor:**
   - Endpoint de salud: `GET /api/v1/health`
   - Listado de bases de datos: `GET /api/v1/databases`
   - Historial de telemetría: `GET /api/v1/databases/{id}/history`
   - Incidentes abiertos: `GET /api/v1/alerts?status=open`

3. **Diagnóstico y Recomendaciones:**
   - Si el Score cae por debajo de 80, sugiere revisar la causa raíz:
     * Si `mem.resident` o `used_memory` supera el 90%: recomienda purga de llaves expiradas o escalado vertical.
     * Si `connections.current` excede el umbral: sugiere verificar fuga de conexiones o configurar connection pooling.
     * Si hay desconexión (Score 0): sugiere verificar cortafuegos, puertos (`27017` / `6379`) y estado del contenedor Docker.

---

## 💬 Ejemplos de Prompt para el Agente

```markdown
Usuario: @dbhealth revisa el estado de Redis.
Agente: Consultando DB Health Monitor API...
        ⚡ Redis Caché (redis-cache-main):
        • Health Score: 🟢 95/100 (Saludable)
        • Memoria en uso: 42.8 MB
        • Latencia: 0.6 ms
        • Conexiones activas: 45
        No se registran anomalías ni umbrales excedidos.
```
