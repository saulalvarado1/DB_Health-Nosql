import { PageHeading, Panel } from '../components/ui'

export function DocumentationPage() {
  return (
    <div className="content-stack">
      <PageHeading
        title="Documentación Técnica"
        description="Especificación de arquitectura, modelo de telemetría y ecosistema de integraciones en producción."
      />

      <div className="grid-two">
        <Panel
          title="🏛️ Arquitectura del Sistema (Modular Monolith)"
          description="Diseño desacoplado con separación estricta de responsabilidades y persistencia en 3FN."
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.92rem', lineHeight: '1.6' }}>
            <p>
              <strong>DB Health Monitor</strong> está construido como un monolito modular de alto rendimiento que opera de forma <em>agentless</em> (sin agentes en servidores de clientes).
            </p>
            <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <li>
                <strong>Capa de Transporte (FastAPI):</strong> Rutas REST tipadas con validación Pydantic v2 y OpenAPI interactivo.
              </li>
              <li>
                <strong>Capa de Dominio & Servicios:</strong> Evaluación determinista de salud y orquestación de alertas independientes de cualquier base de datos específica.
              </li>
              <li>
                <strong>Capa de Conectores (Agentless):</strong> Comandos nativos de solo lectura (<code>serverStatus</code> en MongoDB, <code>INFO/PING</code> en Redis).
              </li>
              <li>
                <strong>Persistencia Relacional (PostgreSQL):</strong> Almacenamiento en Tercera Forma Normal (3FN) con índices optimizados para series temporales de telemetría.
              </li>
              <li>
                <strong>Worker Asíncrono de Monitoreo:</strong> Demonio en segundo plano con bloqueo concurrente <code>SKIP LOCKED</code> que garantiza cero colisiones entre procesos.
              </li>
            </ul>
          </div>
        </Panel>

        <Panel
          title="🛡️ Seguridad & Aislamiento Multi-Tenant"
          description="Políticas de privacidad y protección de secretos de nivel corporativo."
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.92rem', lineHeight: '1.6' }}>
            <p>
              Cada cuenta de usuario opera en un entorno estrictamente aislado con cifrado simétrico en reposo:
            </p>
            <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <li>
                <strong>Cifrado Fernet (AES-128):</strong> Las URIs y credenciales de conexión se cifran con claves criptográficas antes de persistirse.
              </li>
              <li>
                <strong>Argon2id & JWT:</strong> Contraseñas hasheadas con factor de coste de memoria; sesiones sin estado firmadas con algoritmo HMAC-SHA256.
              </li>
              <li>
                <strong>Aislamiento Estricto:</strong> Claves foráneas (<code>owner_id</code>) y restricciones de base de datos impiden que cualquier usuario acceda a instancias ajenas.
              </li>
              <li>
                <strong>Cuentas de Mínimo Privilegio:</strong> Los conectores solo leen contadores y nunca modifican ni consultan datos de los clientes.
              </li>
            </ul>
          </div>
        </Panel>
      </div>

      <Panel
        title="📊 Modelo de Telemetrías e Historial (PostgreSQL)"
        description="Estructura de persistencia inmutable para diagnósticos y series temporales."
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
          <div style={{ background: 'var(--surface-raised)', padding: '16px', borderRadius: 'var(--radius)' }}>
            <h3 style={{ fontSize: '1rem', color: '#10b981', marginBottom: '8px' }}>metric_samples</h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Registra cada ciclo de muestreo periódico (por defecto 30 segundos), marca de tiempo <code>collected_at</code> y estado de disponibilidad del clúster.
            </p>
          </div>
          <div style={{ background: 'var(--surface-raised)', padding: '16px', borderRadius: 'var(--radius)' }}>
            <h3 style={{ fontSize: '1rem', color: '#10b981', marginBottom: '8px' }}>metric_values</h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Telemetrías atómicas normalizadas (latencia en ms, bytes de memoria RAM utilizados, conexiones activas, operaciones/segundo).
            </p>
          </div>
          <div style={{ background: 'var(--surface-raised)', padding: '16px', borderRadius: 'var(--radius)' }}>
            <h3 style={{ fontSize: '1rem', color: '#10b981', marginBottom: '8px' }}>health_assessments</h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Cálculo histórico del <strong>Health Score (0 a 100)</strong> y estado semafórico (🟢 Saludable, 🟡 Advertencia, 🔴 Crítico).
            </p>
          </div>
          <div style={{ background: 'var(--surface-raised)', padding: '16px', borderRadius: 'var(--radius)' }}>
            <h3 style={{ fontSize: '1rem', color: '#10b981', marginBottom: '8px' }}>alerts</h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Ciclo de vida y deduplicación de incidentes generados por transgresión de umbrales con estampa de resolución.
            </p>
          </div>
        </div>
      </Panel>

      <Panel
        title="🔌 Ecosistema de Integraciones Externas"
        description="Cumplimiento y homologación de herramientas complementarias conectadas a la plataforma."
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ borderLeft: '3px solid #10b981', paddingLeft: '14px' }}>
            <h3 style={{ fontSize: '1rem', margin: '0 0 4px 0' }}>
              1. Visual Studio Code — Extensión Oficial de Observabilidad
            </h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Publicada en el <strong>Marketplace de Microsoft</strong> (<code>Grupo3UPTFAING.db-health-monitor-nosql</code>). Permite a los desarrolladores ver el Health Score, latencia y consumo de memoria directamente en la barra lateral (Activity Bar) y barra de estado de su editor con auto-refresco en segundo plano cada 30s.
            </p>
          </div>

          <div style={{ borderLeft: '3px solid #3b82f6', paddingLeft: '14px' }}>
            <h3 style={{ fontSize: '1rem', margin: '0 0 4px 0' }}>
              2. Google Cloud Platform — Autenticación Federada (OAuth 2.0)
            </h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Integrada con Google Identity Platform en modo <strong>Producción</strong>, permitiendo acceso seguro y sin contraseñas para cualquier usuario con cuenta de Google bajo el dominio oficial <code>https://dbhealth.alvarado1.tech</code>.
            </p>
          </div>

          <div style={{ borderLeft: '3px solid #f59e0b', paddingLeft: '14px' }}>
            <h3 style={{ fontSize: '1rem', margin: '0 0 4px 0' }}>
              3. GitHub — Apertura Automatizada de Incidencias (Issues API)
            </h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Cuando una base de datos entra en estado crítico o pierde conectividad de réplica, el motor de eventos de la plataforma despacha automáticamente un ticket en el repositorio GitHub configurado con la telemetría del error para resolución DevOps.
            </p>
          </div>

          <div style={{ borderLeft: '3px solid #06b6d4', paddingLeft: '14px' }}>
            <h3 style={{ fontSize: '1rem', margin: '0 0 4px 0' }}>
              4. Telegram — Alertas Push en Tiempo Real (Bot API)
            </h3>
            <p style={{ fontSize: '0.88rem', margin: 0, color: 'var(--text-muted)' }}>
              Notificaciones push instantáneas dirigidas al canal o chat del DBA ante violaciones de umbrales con control de duplicación activa (deduplication key).
            </p>
          </div>
        </div>
      </Panel>

      <Panel
        title="🌐 Infraestructura y Despliegue en la Nube"
        description="Especificaciones del entorno de producción en vivo."
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', fontSize: '0.9rem' }}>
          <div>
            <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem' }}>Dominio en Producción</span>
            <a href="https://dbhealth.alvarado1.tech" target="_blank" rel="noopener noreferrer" style={{ color: '#10b981', fontWeight: 600 }}>
              https://dbhealth.alvarado1.tech ↗
            </a>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem' }}>Infraestructura de Hosting</span>
            <strong>OVHcloud VPS-1 (Virginia, EE.UU.)</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem' }}>Sistema Operativo</span>
            <strong>Debian 12 Bookworm (Cloud Kernel)</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem' }}>Red & Seguridad Edge</span>
            <strong>Cloudflare CDN + Full SSL/TLS</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem' }}>Orquestación</span>
            <strong>Docker Compose (5 Servicios)</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', display: 'block', fontSize: '0.8rem' }}>API Health Endpoint</span>
            <a href="https://dbhealth.alvarado1.tech/api/v1/health" target="_blank" rel="noopener noreferrer" style={{ color: '#60a5fa', fontWeight: 600 }}>
              /api/v1/health ↗
            </a>
          </div>
        </div>
      </Panel>
    </div>
  )
}
