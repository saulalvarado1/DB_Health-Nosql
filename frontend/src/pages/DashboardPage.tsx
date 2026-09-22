import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { DashboardSnapshot } from '../services/dashboard'
import { EmptyState, ErrorNotice, LoadingState, PageHeading, Panel, StatusBadge } from '../components/ui'
import { formatDate } from '../core/format'
import { getErrorMessage } from '../core/errors'
import { loadDashboard } from '../services/dashboard'

export function DashboardPage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function refresh() {
    setLoading(true)
    setError('')
    try {
      setSnapshot(await loadDashboard())
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    loadDashboard()
      .then((response) => {
        if (active) setSnapshot(response)
      })
      .catch((requestError: unknown) => {
        if (active) setError(getErrorMessage(requestError))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const stats = useMemo(() => {
    const databases = snapshot?.databases ?? []
    return {
      total: databases.length,
      enabled: databases.filter(({ database }) => database.is_enabled).length,
      healthy: databases.filter(({ latest }) => latest?.health_status === 'healthy').length,
      critical: databases.filter(({ latest }) => latest?.health_status === 'critical').length,
      openAlerts: snapshot?.alerts.filter((alert) => alert.status === 'open').length ?? 0,
    }
  }, [snapshot])

  return (
    <div className="page">
      <PageHeading
        eyebrow="Resumen operativo"
        title="Dashboard de salud"
        description="Estado más reciente de tus instancias MongoDB y Redis."
        action={<button className="text-action" onClick={() => void refresh()}>Actualizar</button>}
      />

      {error && <ErrorNotice message={error} />}
      {loading && !snapshot ? <LoadingState /> : (
        <>
          <section className="metric-grid" aria-label="Indicadores principales">
            <article className="metric-card"><span>Instancias</span><strong>{stats.total}</strong><small>{stats.enabled} habilitadas</small></article>
            <article className="metric-card metric-card--healthy"><span>Saludables</span><strong>{stats.healthy}</strong><small>Última evaluación</small></article>
            <article className="metric-card metric-card--critical"><span>Críticas</span><strong>{stats.critical}</strong><small>Requieren revisión</small></article>
            <article className="metric-card metric-card--warning"><span>Alertas abiertas</span><strong>{stats.openAlerts}</strong><small>Condiciones activas</small></article>
          </section>

          <div className="dashboard-grid">
            <Panel
              title="Estado de instancias"
              description="La carga del historial se limita a cuatro solicitudes simultáneas."
              action={<Link className="text-action" to="/databases">Ver todas</Link>}
            >
              {snapshot?.databases.length ? (
                <div className="instance-list">
                  {snapshot.databases.slice(0, 6).map(({ database, latest }) => (
                    <Link to={`/databases/${database.id}`} className="instance-row" key={database.id}>
                      <span className={`engine-mark engine-mark--${database.engine}`} aria-hidden="true">
                        {database.engine === 'redis' ? 'R' : 'M'}
                      </span>
                      <span className="instance-row__main">
                        <strong>{database.name}</strong>
                        <small>{database.engine.toUpperCase()} · cada {database.interval_seconds}s</small>
                      </span>
                      <StatusBadge status={latest?.health_status ?? 'unknown'} />
                      <span className="score">{latest ? `${latest.health_score}/100` : '—'}</span>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="Aún no hay instancias"
                  message="Registra una conexión de solo lectura para comenzar el monitoreo."
                  action={<Link className="button button--primary" to="/databases/new">Registrar instancia</Link>}
                />
              )}
            </Panel>

            <Panel
              title="Alertas recientes"
              description="Las alertas resueltas permanecen como evidencia histórica."
              action={<Link className="text-action" to="/alerts">Ver alertas</Link>}
            >
              {snapshot?.alerts.length ? (
                <div className="alert-list">
                  {snapshot.alerts.slice(0, 5).map((alert) => (
                    <article className="alert-row" key={alert.id}>
                      <div>
                        <StatusBadge status={alert.severity} />
                        <p>{alert.message}</p>
                        <small>{formatDate(alert.created_at)}</small>
                      </div>
                      <StatusBadge status={alert.status} />
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState title="Sin alertas" message="No se han registrado condiciones de advertencia o críticas." />
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  )
}
