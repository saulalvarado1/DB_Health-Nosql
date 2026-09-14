# Modelo de datos — DB Health Monitor

Este esquema está diseñado para PostgreSQL y sigue tercera forma normal (3FN).
Cada hecho se almacena una vez: los motores y métricas son catálogos, los
umbrales se reutilizan mediante perfiles y cada valor recolectado es atómico.

```text
users 1 ── N monitored_databases N ── 1 database_engines
                    │ 1
                    ├── 1 monitoring_schedules
                    ├── 1 database_threshold_profiles N ── 1 threshold_profiles
                    │                                      │ 1
                    │                                      └── N threshold_rules N ── 1 metric_definitions
                    │
                    └── N metric_samples 1 ── N metric_values N ── 1 metric_definitions
                                      │ 1
                                      └── 1 health_assessments

monitored_databases 1 ── N alerts
```

| Grupo | Tablas | Propósito |
|---|---|---|
| Identidad | `users` | Cuentas de acceso a la plataforma. |
| Catálogos | `database_engines`, `metric_definitions` | Describe motores y métricas válidas, sin duplicarlas por instancia. |
| Configuración | `monitored_databases`, `monitoring_schedules` | Define qué se monitoriza y con qué frecuencia. La URI se almacena cifrada. |
| Reglas | `threshold_profiles`, `threshold_rules`, `database_threshold_profiles` | Permite reutilizar umbrales entre instancias del mismo usuario y motor. |
| Historial | `metric_samples`, `metric_values`, `health_assessments` | Guarda cada recolección y sus valores en filas atómicas. |
| Incidentes | `alerts` | Conserva alertas y su ciclo de vida sin borrar el historial. |

## Cómo se aplican las normas de normalización

**Primera forma normal (1FN).** `metric_values` guarda un único valor por
`sample_id` y `metric_definition_id`; no hay columnas repetidas como
`cpu_1`, `cpu_2` o listas JSON de métricas. La restricción única impide dos
valores para la misma métrica en una muestra.

**Segunda forma normal (2FN).** Los datos descriptivos de una métrica (`unidad`,
`nombre`, `descripción`) viven exclusivamente en `metric_definitions`, no en
los valores históricos. Las reglas de umbral dependen de un perfil y una
métrica completos, no de una parte de la relación.

**Tercera forma normal (3FN).** Motor, usuario, perfil, programación y alerta
son entidades independientes. Por ejemplo, una muestra conoce la instancia
monitorizada, pero el nombre del motor se obtiene por la clave foránea; cambiar
el nombre de un motor no requiere actualizar millones de muestras.

## Integridad y rendimiento

- Las claves foráneas conservan referencias válidas y eliminan datos dependientes
  cuando corresponde.
- Las URI de conexión se guardan cifradas; las claves de cifrado no se persisten
  en PostgreSQL.
- `metric_samples(monitored_database_id, collected_at)` acelera el historial por
  instancia y rango de tiempo.
- `alerts(monitored_database_id, status)` acelera el panel de alertas activas.
- Las muestras no deben editarse: son evidencia histórica. Las agregaciones y
  políticas de retención se incorporarán en una migración posterior.
