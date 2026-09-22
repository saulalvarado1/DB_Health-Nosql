import { useEffect, useMemo, useState } from 'react'

import type { Alert, AlertStatus, MonitoredDatabase } from '../api/contracts'
import { alertsApi, databasesApi } from '../api/resources'
import { Button, EmptyState, ErrorNotice, LoadingState, PageHeading, Panel, StatusBadge } from '../components/ui'
import { getErrorMessage } from '../core/errors'
import { formatDate } from '../core/format'

type AlertFilter = 'all' | AlertStatus

const filters: Array<{ value: AlertFilter; label: string }> = [
  { value: 'all', label: 'Todas' },
  { value: 'open', label: 'Abiertas' },
  { value: 'acknowledged', label: 'Reconocidas' },
  { value: 'resolved', label: 'Resueltas' },
]

export function AlertsPage() {
  const [filter, setFilter] = useState<AlertFilter>('all')
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [databases, setDatabases] = useState<MonitoredDatabase[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [changingId, setChangingId] = useState<string | null>(null)

  async function loadAlerts() {
    setLoading(true)
    setError('')
    try {
      const [alertResponse, databaseResponse] = await Promise.all([
        alertsApi.list(filter === 'all' ? undefined : filter),
        databasesApi.list(),
      ])
      setAlerts(alertResponse)
      setDatabases(databaseResponse)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([
      alertsApi.list(filter === 'all' ? undefined : filter),
      databasesApi.list(),
    ])
      .then(([alertResponse, databaseResponse]) => {
        if (!active) return
        setAlerts(alertResponse)
        setDatabases(databaseResponse)
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
  }, [filter])

  const databaseNames = useMemo(
    () => new Map(databases.map((database) => [database.id, database.name])),
    [databases],
  )

  async function acknowledge(alert: Alert) {
    setChangingId(alert.id)
    setError('')
    try {
      const updated = await alertsApi.acknowledge(alert.id)
      setAlerts((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setChangingId(null)
    }
  }

  return (
    <div className="page">
      <PageHeading
        eyebrow="Eventos de umbral"
        title="Alertas"
        description="Las alertas se resuelven automáticamente cuando la métrica vuelve a un rango aceptable."
        action={<button className="text-action" onClick={() => void loadAlerts()}>Actualizar</button>}
      />

      {error && <ErrorNotice message={error} />}

      <Panel>
        <div className="filter-tabs" role="group" aria-label="Filtrar alertas">
          {filters.map((item) => (
            <button key={item.value} type="button" className={filter === item.value ? 'filter-tabs__active' : ''} onClick={() => setFilter(item.value)}>
              {item.label}
            </button>
          ))}
        </div>

        {loading ? <LoadingState /> : alerts.length ? (
          <div className="alert-cards">
            {alerts.map((alert) => (
              <article className={`alert-card alert-card--${alert.severity}`} key={alert.id}>
                <div className="alert-card__status"><StatusBadge status={alert.severity} /><StatusBadge status={alert.status} /></div>
                <div className="alert-card__body">
                  <h2>{databaseNames.get(alert.monitored_database_id) ?? 'Instancia no disponible'}</h2>
                  <p>{alert.message}</p>
                  <dl>
                    <div><dt>Creada</dt><dd>{formatDate(alert.created_at)}</dd></div>
                    <div><dt>Actualizada</dt><dd>{formatDate(alert.updated_at)}</dd></div>
                    {alert.resolved_at && <div><dt>Resuelta</dt><dd>{formatDate(alert.resolved_at)}</dd></div>}
                  </dl>
                </div>
                {alert.status === 'open' && (
                  <Button variant="secondary" busy={changingId === alert.id} onClick={() => void acknowledge(alert)}>Reconocer alerta</Button>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="Sin alertas en este estado" message="No hay eventos que coincidan con el filtro seleccionado." />
        )}
      </Panel>
    </div>
  )
}
