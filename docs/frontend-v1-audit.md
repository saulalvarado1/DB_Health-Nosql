# Auditoría del frontend V1 — DB Health Monitor

Fecha: 22 de septiembre de 2026
Alcance: primera implementación funcional del cliente React, adaptada desde la
referencia visual de Stitch al contrato real del backend V1.

## Resultado

El frontend implementa autenticación, dashboard, inventario y registro de
instancias, detalle e historial, recolección manual, configuración de umbrales
y ciclo de reconocimiento de alertas. El inventario permite abrir una instancia
desde toda su fila sin interferir con Pausar o Eliminar, y el detalle actualiza
el historial automáticamente sin duplicar el trabajo del worker. No incorpora
las funciones ficticias de la plantilla, como SSO, MFA, organizaciones,
PagerDuty, consultas lentas, topología, predicción o resolución manual de
alertas.

## Arquitectura

- `api`: contratos TypeScript equivalentes a los esquemas FastAPI y un único
  cliente HTTP.
- `auth`: proveedor, contexto y hook de sesión independientes.
- `services`: composición de lecturas, con concurrencia limitada para el
  dashboard.
- `pages`: coordinación de los casos de uso visibles.
- `components`: presentación reutilizable sin acceso directo a la API.
- `core`: configuración pública, token de sesión, errores y formato.
- `hooks`: actualización periódica reutilizable, sin solicitudes superpuestas y
  consciente de la visibilidad de la pestaña.

La interfaz usa React, TypeScript y CSS local. No ejecuta el HTML ni los scripts
exportados por Stitch y no depende de Tailwind por CDN, Google Fonts, imágenes
remotas ni bibliotecas de gráficos.

## Controles de seguridad

- No existen credenciales, tokens ni URI reales en el código.
- `VITE_API_BASE_URL` rechaza credenciales embebidas y exige HTTPS salvo en
  loopback de desarrollo.
- El Bearer token se envía únicamente en `Authorization`, no en URL ni cookies,
  y permanece en `sessionStorage` hasta cerrar la pestaña, cerrar sesión o
  recibir un `401`.
- El campo de URI utiliza un control de contraseña, comienza vacío y se limpia
  después del registro.
- Las respuestas nunca presentan la URI y la vista de historial no muestra
  excepciones internas crudas.
- No se usa `dangerouslySetInnerHTML`, `eval`, almacenamiento persistente,
  scripts remotos ni mensajes de depuración.
- React escapa nombres y mensajes antes de representarlos.
- La compilación de producción no genera source maps.

La aplicación cliente siempre puede ser inspeccionada por el navegador. La
protección de recursos continúa en el backend mediante JWT, pertenencia por
usuario y cifrado de secretos; no depende de ocultar JavaScript.

## Evidencia ejecutada

```text
npm run lint   → sin errores ni advertencias
npm test       → 7 archivos, 21 pruebas aprobadas
npm run build  → compilación de producción correcta
npm audit --omit=dev → 0 vulnerabilidades
run-e2e.ps1    → 1 prueba E2E aprobada en Microsoft Edge
pytest -m "not integration" → 45 passed, 3 deselected, 2 warnings
ruff check     → All checks passed
```

La pantalla de acceso se verificó visualmente en 1440×900 y 390×844. También se
comprobó manualmente con Redis real el registro desde la interfaz, el historial
periódico, la tendencia y la navegación desde dashboard e inventario. La
integración automatizada actual confirma 27 métricas Redis y 20 MongoDB;
la prueba del detalle verifica que todo el catálogo de la última muestra se
represente en grupos de prioridad junto con su estado, fundamento y explicación,
y que un intento fallido conserve como referencia la última muestra correcta.
Las pruebas cubren
además la actualización del historial, la
suspensión en pestañas ocultas, la prevención de solicitudes superpuestas, las
acciones independientes de las filas y los formatos de fecha y unidades. No
hubo errores ni advertencias en la consola del navegador.

El E2E levanta PostgreSQL, API, worker, frontend, Redis y MongoDB en un proyecto
Docker temporal. Desde un navegador real valida registro y nuevo login, alta de
ambos motores, recolección automática y manual, catálogos de 27 y 20 métricas,
edición de umbrales, apertura, reconocimiento y resolución de una alerta, pausa,
reactivación y eliminación. La ejecución descubrió y permitió corregir una
incompatibilidad entre el borrado ORM y la cascada de alertas en PostgreSQL.

## Riesgos y trabajo pendiente

| Prioridad | Hallazgo | Condición de cierre |
|---|---|---|
| Media | El token es accesible a JavaScript mientras vive en `sessionStorage`. | Si el modelo de despliegue lo permite, migrar a una cookie `HttpOnly`, `Secure` y `SameSite`, definiendo la protección CSRF correspondiente. |
| Media | El dashboard consulta una muestra por instancia. | Añadir un endpoint agregado de estado más reciente; mientras tanto el cliente limita la concurrencia a cuatro solicitudes. |
| Media | No se ha validado capacidad en infraestructura objetivo. | Ejecutar la prueba de carga acordada y medir p95, throughput y errores. |
| Media | Falta validar HTTPS y navegadores en el proveedor cloud elegido. | Ejecutar E2E contra un entorno de ensayo servido con certificado válido y registrar compatibilidad. |

## Dictamen

El frontend constituye una base funcional, mantenible y coherente con el
backend V1. Su calidad local y su contenedor con proxy/cabeceras de producción
están validados, incluido el recorrido E2E con servicios aislados. La V1 todavía
requiere un ensayo en la nube, carga y observabilidad antes de considerarse
preparada para producción.
