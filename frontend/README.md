# Frontend — DB Health Monitor V1

Cliente React/TypeScript para el backend FastAPI del proyecto. Implementa el
alcance real de V1: autenticación, inventario MongoDB/Redis, recolección e
historial, umbrales y alertas.

## Ejecución local

Con el backend escuchando en `127.0.0.1:8000`:

```powershell
cd frontend
npm install
npm run dev
```

Vite publica la interfaz en `http://127.0.0.1:5173` y redirige `/api` al
backend. Para otro despliegue se puede definir únicamente la dirección pública
de la API:

```dotenv
VITE_API_BASE_URL=/api/v1
```

Una variable `VITE_*` siempre es pública dentro del navegador. Por eso esta
configuración nunca debe contener contraseñas, tokens ni URI de bases
monitorizadas.

## Arquitectura

- `src/api`: contratos de FastAPI y transporte HTTP centralizado.
- `src/auth`: estado y ciclo de la sesión.
- `src/services`: composición de casos de lectura, como el dashboard.
- `src/pages`: pantallas y coordinación de casos de uso.
- `src/components`: componentes visuales sin lógica de negocio.
- `src/core`: configuración, almacenamiento de sesión y formateadores.
- `src/hooks`: comportamiento reutilizable de interfaz, como la actualización
  periódica y consciente de la visibilidad de la pestaña.

El dashboard limita a cuatro las solicitudes simultáneas de historial. Cuando
el volumen de instancias aumente, conviene sustituir esas consultas por un
endpoint agregado en el backend.

La pantalla de detalle vuelve a consultar únicamente el historial a la mitad
del intervalo configurado, con un mínimo de cinco segundos. No ejecuta
recolecciones: el worker sigue siendo el único responsable de generarlas. La
consulta automática se detiene cuando la instancia está pausada, la pantalla se
desmonta o la pestaña queda oculta, y evita solicitudes superpuestas.

## Seguridad

- No contiene secretos ni valores de conexión predeterminados.
- Las URI se escriben en un control de contraseña, se envían solo en el cuerpo
  del registro y se limpian después de una respuesta correcta.
- El token Bearer permanece en `sessionStorage`, nunca en `localStorage`, una
  URL o un elemento visual. Se elimina al cerrar sesión o recibir un `401`.
- No se utiliza HTML dinámico, scripts CDN ni recursos remotos. React escapa el
  contenido entregado por usuarios o por la API.
- Las URL remotas de API deben usar HTTPS y no pueden contener credenciales.
- La compilación de producción no genera source maps.

El código del frontend siempre es descargable e inspeccionable por el
navegador. La seguridad no depende de ocultarlo: el backend continúa validando
JWT, pertenencia de recursos y cifrado de credenciales.

En producción se recomienda servir frontend y API bajo el mismo origen,
habilitar HTTPS y configurar en el proxy los encabezados `Content-Security-Policy`,
`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer` y una política de `frame-ancestors 'none'`.

## Verificación

```powershell
npm run lint
npm test
npm run build
```
