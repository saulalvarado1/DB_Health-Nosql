import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import type { HistoryTimeRange, MonitoredDatabase, MonitoringHistory } from '../api/contracts'
import { databasesApi } from '../api/resources'
import { HealthChart } from '../components/HealthChart'
import { MetricCatalog } from '../components/MetricCatalog'
import { Button, EmptyState, ErrorNotice, LoadingState, PageHeading, Panel, StatusBadge, SuccessNotice } from '../components/ui'
import { getErrorMessage } from '../core/errors'
import { formatDate, formatDateWithSeconds, formatMetric, formatTimeWithSeconds } from '../core/format'
import { useAutoRefresh } from '../hooks/useAutoRefresh'

const featuredMetricCodes: Record<MonitoredDatabase['engine'], string[]> = {
  mongodb: ['availability', 'connections_current', 'memory_resident_mb'],
  redis: ['availability', 'connected_clients', 'memory_usage_percent'],
}

const TIME_RANGES: { id: HistoryTimeRange; label: string }[] = [
  { id: '1h', label: '1 hora' },
  { id: '6h', label: '6 horas' },
  { id: '24h', label: '24 horas' },
  { id: '7d', label: '7 días' },
  { id: 'all', label: 'Todo' },
]

export function DatabaseDetailPage() {
  const { databaseId = '' } = useParams()
  const [database, setDatabase] = useState<MonitoredDatabase | null>(null)
  const [history, setHistory] = useState<MonitoringHistory[]>([])
  const [selectedRange, setSelectedRange] = useState<HistoryTimeRange>('all')
  const [name, setName] = useState('')
  const [intervalSeconds, setIntervalSeconds] = useState(30)
  const [error, setError] = useState('')
  const [refreshError, setRefreshError] = useState('')
  const [success, setSuccess] = useState('')
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyAction, setBusyAction] = useState<
    'collect' | 'save' | 'toggle' | 'export-csv' | 'export-json' | 'save-telegram' | 'test-telegram' | null
  >(null)

  const [telegramEnabled, setTelegramEnabled] = useState(false)
  const [telegramChatId, setTelegramChatId] = useState('')
  const [telegramBotToken, setTelegramBotToken] = useState('')
  const [notifyWarning, setNotifyWarning] = useState(false)
  const [notifyCritical, setNotifyCritical] = useState(true)
  const [notifyRecovery, setNotifyRecovery] = useState(true)
  const [telegramSuccess, setTelegramSuccess] = useState('')
  const [telegramError, setTelegramError] = useState('')
  const [showTelegramGuide, setShowTelegramGuide] = useState(false)

  const exportReport = useCallback(
    async (format: 'csv' | 'json') => {
      if (!databaseId) return
      setBusyAction(format === 'csv' ? 'export-csv' : 'export-json')
      setError('')
      try {
        await databasesApi.exportReport(databaseId, format, 100, selectedRange)
      } catch (requestError) {
        setError(getErrorMessage(requestError))
      } finally {
        setBusyAction(null)
      }
    },
    [databaseId, selectedRange],
  )

  const refreshHistory = useCallback(
    async (rangeToUse = selectedRange) => {
      const updatedHistory = await databasesApi.history(databaseId, 100, rangeToUse)
      setHistory(updatedHistory)
      setLastUpdatedAt(new Date().toISOString())
    },
    [databaseId, selectedRange],
  )

  const handleRangeChange = useCallback(
    async (newRange: HistoryTimeRange) => {
      setSelectedRange(newRange)
      setError('')
      try {
        const updatedHistory = await databasesApi.history(databaseId, 100, newRange)
        setHistory(updatedHistory)
        setLastUpdatedAt(new Date().toISOString())
      } catch (requestError) {
        setError(getErrorMessage(requestError))
      }
    },
    [databaseId],
  )

  const autoRefreshHistory = useCallback(async () => {
    await refreshHistory()
    setRefreshError('')
  }, [refreshHistory])

  const handleAutoRefreshError = useCallback(() => {
    setRefreshError('No se pudo actualizar el historial. Se reintentará automáticamente.')
  }, [])

  useEffect(() => {
    if (!databaseId) return
    let active = true
    Promise.all([databasesApi.get(databaseId), databasesApi.history(databaseId, 50)])
      .then(([databaseResponse, historyResponse]) => {
        if (!active) return
        setDatabase(databaseResponse)
        setName(databaseResponse.name)
        setIntervalSeconds(databaseResponse.interval_seconds)
        setTelegramEnabled(databaseResponse.telegram_notifications_enabled ?? false)
        setTelegramChatId(databaseResponse.telegram_chat_id ?? '')
        setNotifyWarning(databaseResponse.notify_on_warning ?? false)
        setNotifyCritical(databaseResponse.notify_on_critical ?? true)
        setNotifyRecovery(databaseResponse.notify_on_recovery ?? true)
        setHistory(historyResponse)
        setLastUpdatedAt(new Date().toISOString())
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
  }, [databaseId])

  const autoRefreshIntervalMs = Math.max(5_000, (database?.interval_seconds ?? 30) * 500)
  useAutoRefresh({
    callback: autoRefreshHistory,
    enabled: database?.is_enabled === true,
    intervalMs: autoRefreshIntervalMs,
    onError: handleAutoRefreshError,
  })

  const latest = history[0] ?? null
  const latestSuccessfulSample = useMemo(
    () => history.find((sample) => sample.collection_succeeded && sample.metrics.length > 0) ?? null,
    [history],
  )
  const metricSample = latest?.metrics.length ? latest : latestSuccessfulSample
  const latestMetrics = useMemo(() => metricSample?.metrics ?? [], [metricSample])
  const isShowingPreviousMetrics = Boolean(
    latest && metricSample && latest.sample_id !== metricSample.sample_id,
  )
  const featuredMetrics = useMemo(() => {
    if (!database) return []
    const metricsByCode = new Map(latestMetrics.map((metric) => [metric.code, metric]))
    return featuredMetricCodes[database.engine]
      .map((code) => metricsByCode.get(code))
      .filter((metric) => metric !== undefined)
  }, [database, latestMetrics])

  async function collectNow() {
    setBusyAction('collect')
    setError('')
    setSuccess('')
    try {
      const result = await databasesApi.collect(databaseId)
      setSuccess(
        result.collection_succeeded
          ? `Recolección terminada: ${result.metric_count} métricas procesadas.`
          : 'La recolección terminó sin conexión; se guardó un resultado seguro.',
      )
      await refreshHistory()
      setRefreshError('')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusyAction(null)
    }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusyAction('save')
    setError('')
    setSuccess('')
    try {
      const updated = await databasesApi.update(databaseId, {
        name: name.trim(),
        interval_seconds: intervalSeconds,
      })
      setDatabase(updated)
      setSuccess('Configuración actualizada.')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusyAction(null)
    }
  }

  async function toggleMonitoring() {
    if (!database) return
    setBusyAction('toggle')
    setError('')
    try {
      setDatabase(await databasesApi.update(databaseId, { is_enabled: !database.is_enabled }))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusyAction(null)
    }
  }

  async function saveTelegramSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusyAction('save-telegram')
    setTelegramError('')
    setTelegramSuccess('')
    try {
      const updated = await databasesApi.update(databaseId, {
        telegram_notifications_enabled: telegramEnabled,
        telegram_chat_id: telegramChatId.trim() || null,
        telegram_bot_token: telegramBotToken.trim() || undefined,
        notify_on_warning: notifyWarning,
        notify_on_critical: notifyCritical,
        notify_on_recovery: notifyRecovery,
      })
      setDatabase(updated)
      setTelegramBotToken('')
      setTelegramSuccess('Configuración de alertas de Telegram guardada correctamente.')
    } catch (requestError) {
      setTelegramError(getErrorMessage(requestError))
    } finally {
      setBusyAction(null)
    }
  }

  async function testTelegram() {
    setBusyAction('test-telegram')
    setTelegramError('')
    setTelegramSuccess('')
    try {
      const res = await databasesApi.testTelegram(databaseId, {
        chat_id: telegramChatId.trim() || undefined,
        bot_token: telegramBotToken.trim() || undefined,
      })
      setTelegramSuccess(`✅ ${res.message} ¡Revisa tu teléfono!`)
    } catch (requestError) {
      setTelegramError(getErrorMessage(requestError))
    } finally {
      setBusyAction(null)
    }
  }

  if (loading) return <div className="page"><LoadingState /></div>

  return (
    <div className="page">
      <PageHeading
        eyebrow={database?.engine.toUpperCase() ?? 'Instancia'}
        title={database?.name ?? 'Detalle no disponible'}
        description={database
          ? `Registrada el ${formatDate(database.created_at)} · monitoreo cada ${database.interval_seconds}s${lastUpdatedAt ? ` · vista actualizada ${formatTimeWithSeconds(lastUpdatedAt)}` : ''}`
          : undefined}
        action={database && (
          <div className="page-actions">
            <StatusBadge status={database.is_enabled ? 'enabled' : 'disabled'} />
            <Button variant="secondary" busy={busyAction === 'toggle'} onClick={() => void toggleMonitoring()}>
              {database.is_enabled ? 'Pausar' : 'Activar'}
            </Button>
            <Button busy={busyAction === 'collect'} disabled={!database.is_enabled} onClick={() => void collectNow()}>Recolectar ahora</Button>
          </div>
        )}
      />

      {error && <ErrorNotice message={error} />}
      {refreshError && <ErrorNotice message={refreshError} />}
      {success && <SuccessNotice message={success} />}
      {isShowingPreviousMetrics && metricSample && (
        <ErrorNotice
          message={`La última recolección no obtuvo métricas. Se muestran como referencia los últimos valores correctos del ${formatDateWithSeconds(metricSample.collected_at)}.`}
        />
      )}

      {database && (
        <>
          <section className="metric-grid">
            <article className="metric-card"><span>Puntaje de salud</span><strong>{latest ? latest.health_score : '—'}</strong><small>{latest ? <StatusBadge status={latest.health_status} /> : 'Sin muestras'}</small></article>
            {featuredMetrics.map((metric) => (
              <article className="metric-card" key={metric.code}><span>{metric.display_name}</span><strong>{formatMetric(metric.value, metric.unit)}</strong><small className="mono">{metric.code}</small></article>
            ))}
          </section>

          <Panel
            title="Métricas actuales"
            description={metricSample
              ? `${isShowingPreviousMetrics ? 'Última muestra correcta' : 'Última muestra'}: ${formatDateWithSeconds(metricSample.collected_at)}. Abre cada grupo para consultar sus diagnósticos; solo los umbrales configurados afectan el puntaje y las alertas.`
              : 'Todavía no existe una muestra para esta instancia.'}
          >
            {latestMetrics.length ? (
              <MetricCatalog metrics={latestMetrics} />
            ) : (
              <EmptyState
                title="Sin métricas"
                message="Ejecuta una recolección o espera al siguiente ciclo del worker."
              />
            )}
          </Panel>

          <div className="detail-grid">
            <Panel title="Tendencia de salud" description="Puntaje de las últimas 50 evaluaciones.">
              <HealthChart history={history} />
            </Panel>

            <Panel title="Configuración" action={<Link className="text-action" to={`/thresholds?database=${database.id}`}>Editar umbrales</Link>}>
              <form className="form-stack" onSubmit={saveSettings}>
                <label className="field"><span>Nombre</span><input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required /></label>
                <label className="field"><span>Intervalo (segundos)</span><input type="number" value={intervalSeconds} onChange={(event) => setIntervalSeconds(event.target.valueAsNumber)} min={10} max={86_400} required /></label>
                <Button type="submit" busy={busyAction === 'save'}>Guardar cambios</Button>
              </form>
            </Panel>
          </div>

          <Panel
            title="Alertas y Notificaciones a Telegram"
            description="Recibe avisos inmediatos en tu celular ante caídas de servicio o degradación de salud."
            action={
              <button
                type="button"
                className="text-action"
                onClick={() => setShowTelegramGuide((prev) => !prev)}
              >
                {showTelegramGuide ? 'Ocultar guía' : '¿Cómo configurar Telegram?'}
              </button>
            }
          >
            {telegramSuccess && <SuccessNotice message={telegramSuccess} />}
            {telegramError && <ErrorNotice message={telegramError} />}

            {showTelegramGuide && (
              <div className="security-box" style={{ marginBottom: '1.25rem' }}>
                <strong>📱 Cómo vincular Telegram en 3 simples pasos:</strong>
                <ul>
                  <li>
                    <strong>1. Obtén tu Chat ID:</strong> Abre Telegram, busca el bot <code>@userinfobot</code> y presiona <em>Start</em>. Te responderá con tu número de <code>Id</code> personal (ej: <code>123456789</code>).
                  </li>
                  <li>
                    <strong>2. Inicia el bot:</strong> Abre una conversación con tu bot (o con el bot del monitor) y presiona <em>/start</em> para habilitar la recepción de mensajes.
                  </li>
                  <li>
                    <strong>3. Vincula y prueba:</strong> Pega tu Chat ID abajo, activa las alertas y pulsa <em>"Enviar mensaje de prueba a Telegram"</em>.
                  </li>
                </ul>
              </div>
            )}

            <form className="form-stack" onSubmit={saveTelegramSettings}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.25rem 0' }}>
                <input
                  type="checkbox"
                  id="telegram-enabled"
                  checked={telegramEnabled}
                  onChange={(e) => setTelegramEnabled(e.target.checked)}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--primary)' }}
                />
                <label htmlFor="telegram-enabled" style={{ cursor: 'pointer', fontWeight: 600 }}>
                  Activar notificaciones de Telegram para esta base de datos
                </label>
              </div>

              <div className="form-grid" style={{ paddingTop: '0.5rem' }}>
                <label className="field">
                  <span>Chat ID de Telegram</span>
                  <input
                    type="text"
                    value={telegramChatId}
                    onChange={(e) => setTelegramChatId(e.target.value)}
                    placeholder="Ej: 123456789 o -100123456789 (canal/grupo)"
                    disabled={!telegramEnabled}
                  />
                  <small>ID numérico de tu usuario, grupo o canal de Telegram.</small>
                </label>

                <label className="field">
                  <span>
                    Bot Token Personalizado{' '}
                    {database.has_telegram_bot_token && (
                      <span style={{ color: '#6ee7b7', fontSize: '11px', fontWeight: 'bold' }}>
                        (Token guardado ✓)
                      </span>
                    )}
                  </span>
                  <input
                    type="password"
                    value={telegramBotToken}
                    onChange={(e) => setTelegramBotToken(e.target.value)}
                    placeholder={
                      database.has_telegram_bot_token
                        ? 'Dejar en blanco para mantener el actual'
                        : 'Opcional. Se cifra de forma segura'
                    }
                    disabled={!telegramEnabled}
                  />
                  <small>
                    Opcional. Si lo dejas vacío, se usa el bot predeterminado del sistema.
                  </small>
                </label>

                <div className="form-grid__full" style={{ marginTop: '0.25rem' }}>
                  <span
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: 'var(--text)',
                      display: 'block',
                      marginBottom: '0.5rem',
                    }}
                  >
                    Eventos a notificar:
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem' }}>
                    <label
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        cursor: telegramEnabled ? 'pointer' : 'not-allowed',
                        opacity: telegramEnabled ? 1 : 0.6,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={notifyCritical}
                        onChange={(e) => setNotifyCritical(e.target.checked)}
                        disabled={!telegramEnabled}
                        style={{ accentColor: 'var(--critical)' }}
                      />
                      <span>🚨 Crítico y caídas de conexión</span>
                    </label>

                    <label
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        cursor: telegramEnabled ? 'pointer' : 'not-allowed',
                        opacity: telegramEnabled ? 1 : 0.6,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={notifyWarning}
                        onChange={(e) => setNotifyWarning(e.target.checked)}
                        disabled={!telegramEnabled}
                        style={{ accentColor: 'var(--warning)' }}
                      />
                      <span>⚠️ Advertencias de umbral</span>
                    </label>

                    <label
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        cursor: telegramEnabled ? 'pointer' : 'not-allowed',
                        opacity: telegramEnabled ? 1 : 0.6,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={notifyRecovery}
                        onChange={(e) => setNotifyRecovery(e.target.checked)}
                        disabled={!telegramEnabled}
                        style={{ accentColor: 'var(--primary)' }}
                      />
                      <span>✅ Recuperación de salud</span>
                    </label>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
                <Button type="submit" busy={busyAction === 'save-telegram'}>
                  Guardar alertas
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  busy={busyAction === 'test-telegram'}
                  disabled={!telegramChatId.trim()}
                  onClick={() => void testTelegram()}
                >
                  📱 Enviar mensaje de prueba a Telegram
                </Button>
              </div>
            </form>
          </Panel>

          <Panel
            title="Historial de monitoreo"
            description="Las muestras son registros históricos y no se sobrescriben."
            action={
              history.length > 0 ? (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Button
                    variant="secondary"
                    busy={busyAction === 'export-csv'}
                    onClick={() => void exportReport('csv')}
                  >
                    Exportar CSV
                  </Button>
                  <Button
                    variant="secondary"
                    busy={busyAction === 'export-json'}
                    onClick={() => void exportReport('json')}
                  >
                    Exportar JSON
                  </Button>
                </div>
              ) : undefined
            }
          >
            <div
              className="filter-tabs"
              role="group"
              aria-label="Filtrar por rango de tiempo"
              style={{ marginTop: 0, marginBottom: '1rem' }}
            >
              {TIME_RANGES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={selectedRange === item.id ? 'filter-tabs__active' : ''}
                  onClick={() => void handleRangeChange(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {history.length ? (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Fecha</th><th>Recolección</th><th>Salud</th><th>Puntaje</th><th>Métricas</th></tr></thead>
                  <tbody>
                    {history.map((sample) => (
                      <tr key={sample.sample_id}>
                        <td>{formatDateWithSeconds(sample.collected_at)}</td>
                        <td>{sample.collection_succeeded ? 'Correcta' : 'No disponible'}</td>
                        <td><StatusBadge status={sample.health_status} /></td>
                        <td className="mono">{sample.health_score}/100</td>
                        <td>{sample.collection_succeeded ? `${sample.metrics.length} valores` : 'Error de conexión protegido'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <EmptyState title="Sin historial" message="Ejecuta una recolección o espera al siguiente ciclo del worker." />}
          </Panel>
        </>
      )}
    </div>
  )
}
