import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { MonitoredDatabase } from '../api/contracts'
import { databasesApi } from '../api/resources'
import { Button, EmptyState, ErrorNotice, LoadingState, PageHeading, Panel, StatusBadge } from '../components/ui'
import { getErrorMessage } from '../core/errors'
import { formatDate } from '../core/format'

export function DatabasesPage() {
  const navigate = useNavigate()
  const [databases, setDatabases] = useState<MonitoredDatabase[]>([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [changingId, setChangingId] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    databasesApi.list()
      .then((response) => {
        if (active) setDatabases(response)
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

  const filteredDatabases = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('es')
    if (!normalizedQuery) return databases
    return databases.filter(
      (database) =>
        database.name.toLocaleLowerCase('es').includes(normalizedQuery) ||
        database.engine.includes(normalizedQuery),
    )
  }, [databases, query])

  async function toggleDatabase(database: MonitoredDatabase) {
    setChangingId(database.id)
    setError('')
    try {
      const updated = await databasesApi.update(database.id, { is_enabled: !database.is_enabled })
      setDatabases((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setChangingId(null)
    }
  }

  async function removeDatabase(database: MonitoredDatabase) {
    const confirmed = window.confirm(
      `¿Eliminar “${database.name}”? Se perderá su configuración y esta acción no puede deshacerse.`,
    )
    if (!confirmed) return

    setChangingId(database.id)
    setError('')
    try {
      await databasesApi.remove(database.id)
      setDatabases((current) => current.filter((item) => item.id !== database.id))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setChangingId(null)
    }
  }

  return (
    <div className="page">
      <PageHeading
        eyebrow="Inventario"
        title="Bases monitorizadas"
        description="Solo se muestran datos operativos; las URI de conexión nunca regresan desde la API."
        action={<Link className="button button--primary" to="/databases/new">Registrar instancia</Link>}
      />

      {error && <ErrorNotice message={error} />}

      <Panel>
        <div className="toolbar">
          <label className="search-field">
            <span className="sr-only">Buscar por nombre o motor</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por nombre o motor"
            />
          </label>
          <span className="toolbar__count">{filteredDatabases.length} resultados</span>
        </div>

        {loading ? <LoadingState /> : filteredDatabases.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Instancia</th><th>Motor</th><th>Intervalo</th><th>Estado</th><th>Registrada</th><th><span className="sr-only">Acciones</span></th></tr>
              </thead>
              <tbody>
                {filteredDatabases.map((database) => (
                  <tr
                    className="database-table-row"
                    key={database.id}
                    onClick={() => void navigate(`/databases/${database.id}`)}
                  >
                    <td>
                      <Link
                        className="table-link"
                        to={`/databases/${database.id}`}
                        onClick={(event) => event.stopPropagation()}
                      >
                        {database.name}
                      </Link>
                    </td>
                    <td><span className="engine-label"><span className={`engine-mark engine-mark--${database.engine}`} aria-hidden="true">{database.engine === 'redis' ? 'R' : 'M'}</span>{database.engine}</span></td>
                    <td className="mono">{database.interval_seconds}s</td>
                    <td><StatusBadge status={database.is_enabled ? 'enabled' : 'disabled'} /></td>
                    <td>{formatDate(database.created_at)}</td>
                    <td onClick={(event) => event.stopPropagation()}>
                      <div className="row-actions">
                        <Button variant="ghost" busy={changingId === database.id} onClick={() => void toggleDatabase(database)}>
                          {database.is_enabled ? 'Pausar' : 'Activar'}
                        </Button>
                        <Button variant="danger" disabled={changingId === database.id} onClick={() => void removeDatabase(database)}>Eliminar</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title={databases.length ? 'Sin coincidencias' : 'No hay bases registradas'}
            message={databases.length ? 'Prueba con otro nombre o motor.' : 'Registra una conexión MongoDB o Redis de solo lectura.'}
            action={!databases.length && <Link className="button button--primary" to="/databases/new">Registrar instancia</Link>}
          />
        )}
      </Panel>
    </div>
  )
}
