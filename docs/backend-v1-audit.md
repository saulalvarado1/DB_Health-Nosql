# Auditoría del backend V1 — DB Health Monitor

Fecha: 22 de septiembre de 2026
Alcance: cierre del ciclo de monitoreo del backend; no representa el cierre de
la V1 completa del producto.

## Resultado

El backend quedó validado de extremo a extremo contra PostgreSQL, Redis y
MongoDB reales de prueba. La ejecución fue reproducible, no utilizó el archivo
`.env`, no imprimió credenciales y eliminó los contenedores temporales al
terminar.

## Cambios auditados

- `test_real_services_integration.py` valida Redis y MongoDB con usuarios de
  monitoreo de solo lectura.
- `run_real_services_integration.ps1` crea un entorno efímero con imágenes
  fijadas, contraseñas aleatorias y la base exacta `db_health_monitor_test`.
- `config.py` y `main.py` incorporan CORS con una lista explícita y valor seguro
  por defecto.
- `test_cors.py` verifica tanto el origen autorizado como la ausencia de CORS
  cuando no hay configuración.
- `pyproject.toml` registra la marca `real_services`.

## Evidencia ejecutada

### Suite normal

```text
45 passed, 3 skipped, 2 warnings
```

Los tres casos omitidos requieren servicios externos y se ejecutan con el
script aislado.

### Integración aislada completa

Comando:

```powershell
.\scripts\run_real_services_integration.ps1
```

Resultado:

```text
3 passed, 45 deselected, 2 warnings
```

Quedaron acreditados estos escenarios:

- un segundo usuario no puede acceder a datos del primero;
- dos workers respetan `FOR UPDATE SKIP LOCKED` y recuperan reservas vencidas;
- Redis acepta `PING` e `INFO`, pero rechaza `SET`;
- MongoDB acepta `ping` y `serverStatus`, pero rechaza inserciones;
- Redis entrega 27 métricas y MongoDB 20 métricas;
- cada métrica entrega estado, fundamento y explicación sin incluir secretos;
- tres recolecciones Redis conservan tres muestras históricas diferentes;
- las URI almacenadas están cifradas y no aparecen en las respuestas;
- una alerta recorre `open` → `acknowledged` → `resolved`.

### Calidad estática

`ruff check backend` terminó sin errores. Los conectores ampliados y su nueva
migración fueron formateados con Ruff antes de ejecutar la suite.

## Seguridad y limpieza

- Los servicios se publicaron únicamente en `127.0.0.1`.
- Las contraseñas se generaron en memoria y se retiraron junto con las variables
  de entorno al finalizar.
- El script elimina únicamente los contenedores que creó y se detiene si sus
  nombres ya existen.
- Después de la ejecución se comprobó que no quedaran contenedores efímeros y se
  borraron las carpetas temporales de credenciales de validaciones anteriores.

## Hallazgos pendientes para la V1 completa

| Prioridad | Hallazgo | Condición de cierre |
|---|---|---|
| Alta | El frontend React funcional ya existe, pero falta validar el flujo completo contra servicios aislados. | Añadir E2E para autenticación, registro de instancias, panel, historial, umbrales y alertas. |
| Media | No existe una cifra demostrada de capacidad. | Ejecutar k6 o Locust en la infraestructura objetivo y publicar p95, throughput y errores. |
| Media | Observabilidad incompleta. | Añadir métricas operativas y trazabilidad de API/worker sin secretos. |
| Media | Falta validar la operación en el proveedor cloud elegido. | Desplegar un entorno de ensayo con HTTPS, secretos administrados, copias de seguridad y prueba de restauración. |
| Baja | Dos advertencias de deprecación en dependencias de pruebas. | Actualizar FastAPI/Starlette/AnyIO de forma compatible y confirmar la suite. |
| Baja | Nueve archivos preexistentes no cumplen `ruff format --check`. | Formatearlos en un cambio separado para evitar mezclar modificaciones. |

## Dictamen

El bloque de validación con servicios reales del backend está terminado y el
despliegue reproducible local del sistema completo quedó validado en
`deployment-audit.md`. La V1 aún necesita E2E del producto, una ejecución en el
proveedor cloud elegido, prueba de carga y observabilidad antes de afirmar una
capacidad concreta o preparación para producción.
