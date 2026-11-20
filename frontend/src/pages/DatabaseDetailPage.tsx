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
    | 'collect'
    | 'save'
    | 'toggle'
    | 'export-csv'
    | 'export-json'
    | 'save-telegram'
    | 'test-telegram'
    | 'save-github'
    | 'test-github'
    | null
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

  const [githubIssuesEnabled, setGithubIssuesEnabled] = useState(false)
  const [githubRepository, setGithubRepository] = useState('')
  const [githubToken, setGithubToken] = useState('')
  const [githubSuccess, setGithubSuccess] = useState('')
  const [githubError, setGithubError] = useState('')
  const [showGithubGuide, setShowGithubGuide] = useState(false)
  const [showTelegramToken, setShowTelegramToken] = useState(false)
  const [showGithubToken, setShowGithubToken] = useState(false)
  const [lastGithubIssueUrl, setLastGithubIssueUrl] = useState('')
  const [lastGithubIssueNumber, setLastGithubIssueNumber] = useState<number | null>(null)

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
        setGithubIssuesEnabled(databaseResponse.github_issues_enabled ?? false)
        setGithubRepository(databaseResponse.github_repository ?? '')
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

  async function saveGithubSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusyAction('save-github')
    setGithubError('')
    setGithubSuccess('')
    try {
      const updated = await databasesApi.update(databaseId, {
        github_issues_enabled: githubIssuesEnabled,
        github_repository: githubRepository.trim() || null,
        github_token: githubToken.trim() || undefined,
      })
      setDatabase(updated)
      setGithubToken('')
      setGithubSuccess('Configuración de GitHub Issues guardada correctamente.')
    } catch (requestError) {
      setGithubError(getErrorMessage(requestError))
    } finally {
      setBusyAction(null)
    }
  }

  async function testGithubIssue() {
    setBusyAction('test-github')
    setGithubError('')
    setGithubSuccess('')
    try {
      const res = await databasesApi.testGitHubIssue(databaseId, {
        repository: githubRepository.trim() || undefined,
        token: githubToken.trim() || undefined,
      })
      if (res.issue_url) {
        setLastGithubIssueUrl(res.issue_url)
        const parts = res.issue_url.split('/')
        const parsedNumber = Number(parts[parts.length - 1])
        setLastGithubIssueNumber(Number.isNaN(parsedNumber) ? null : parsedNumber)
      }
      setGithubSuccess(
        `✅ ${res.message}${res.issue_url ? ` Enlace: ${res.issue_url}` : ''}`,
      )
    } catch (requestError) {
      setGithubError(getErrorMessage(requestError))
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
      {isShowingPreviousMetrics && metricSample ? (
        <ErrorNotice
          message={`La última recolección no obtuvo métricas${latest?.error_message ? `: ${latest.error_message}` : '.'} Se muestran como referencia los últimos valores correctos del ${formatDateWithSeconds(metricSample.collected_at)}.`}
        />
      ) : (
        latest && !latest.collection_succeeded && latest.error_message && (
          <ErrorNotice message={`Último fallo de conexión: ${latest.error_message}`} />
        )
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

          {/* Hub de Notificaciones y Canales DevOps (Telegram & GitHub) */}
          <section className="integration-hub" aria-label="Canales de Notificación e Integraciones">
            <div className="integration-hub__header">
              <div>
                <span className="eyebrow">Canales y DevOps</span>
                <h2 style={{ margin: '4px 0', fontSize: '1.25rem', color: 'var(--text)' }}>
                  Canales de Notificación e Incidentes
                </h2>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Alertas push instantáneas a tu teléfono y apertura automatizada de incidencias en tus repositorios de código.
                </p>
              </div>
            </div>

            <div className="channels-grid">
              {/* Tarjeta de Telegram */}
              <div className={`channel-card${telegramEnabled ? ' channel-card--active' : ''}`}>
                <div className="channel-card__header">
                  <div className="channel-card__brand">
                    <div className="channel-card__icon channel-card__icon--telegram" aria-hidden="true">
                      📱
                    </div>
                    <div className="channel-card__title">
                      <h3 style={{ margin: 0, fontSize: '15px' }}>Alertas y Notificaciones a Telegram</h3>
                      <small>Mensajería instantánea a tu teléfono</small>
                    </div>
                  </div>

                  <div className="channel-card__controls">
                    {telegramEnabled && telegramChatId.trim() ? (
                      <span className="badge-pill badge-pill--success">🟢 Conectado</span>
                    ) : telegramEnabled ? (
                      <span className="badge-pill badge-pill--warning">⚠️ Falta Chat ID</span>
                    ) : (
                      <span className="badge-pill badge-pill--muted">⚪ Inactivo</span>
                    )}

                    <label className="toggle-switch" title={telegramEnabled ? 'Desactivar notificaciones de Telegram' : 'Activar notificaciones de Telegram'}>
                      <input
                        type="checkbox"
                        id="telegram-enabled"
                        checked={telegramEnabled}
                        onChange={(e) => setTelegramEnabled(e.target.checked)}
                      />
                      <span className="toggle-slider" aria-hidden="true"></span>
                    </label>
                  </div>
                </div>

                <form className="channel-card__body" onSubmit={saveTelegramSettings}>
                  {telegramSuccess && <SuccessNotice message={telegramSuccess} />}
                  {telegramError && <ErrorNotice message={telegramError} />}

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <button
                      type="button"
                      className="text-action"
                      style={{ fontSize: '0.82rem', fontWeight: 600 }}
                      onClick={() => setShowTelegramGuide((prev) => !prev)}
                    >
                      {showTelegramGuide ? '✕ Ocultar guía' : '💡 ¿Cómo configurar Telegram?'}
                    </button>
                    <a
                      href="https://t.me/userinfobot"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-action"
                      style={{ fontSize: '0.82rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      title="Abrir @userinfobot en Telegram para consultar tu Chat ID"
                    >
                      ↗️ Abrir @userinfobot
                    </a>
                  </div>

                  {showTelegramGuide && (
                    <div className="security-box" style={{ margin: 0 }}>
                      <strong>📱 Cómo vincular Telegram en 3 simples pasos:</strong>
                      <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                        <li>
                          <strong>1. Obtén tu Chat ID:</strong> Abre Telegram, busca <code>@userinfobot</code> y dale <em>Start</em>. Te responderá con tu <code>Id</code> numérico personal (ej: <code>123456789</code>).
                        </li>
                        <li>
                          <strong>2. Inicia el bot:</strong> Abre una conversación con el bot y presiona <em>/start</em> para autorizar el envío de alertas.
                        </li>
                        <li>
                          <strong>3. Vincula y prueba:</strong> Ingresa tu Chat ID abajo y pulsa <em>"Enviar mensaje de prueba a Telegram"</em>.
                        </li>
                      </ul>
                    </div>
                  )}

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
                    <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>
                        Bot Token Personalizado{' '}
                        {database.has_telegram_bot_token && (
                          <span style={{ color: '#6ee7b7', fontSize: '11px', fontWeight: 'bold' }}>
                            (Token guardado ✓)
                          </span>
                        )}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>🛡️ Cifrado AES-256</span>
                    </span>
                    <div className="input-eye-wrapper">
                      <input
                        type={showTelegramToken ? 'text' : 'password'}
                        value={telegramBotToken}
                        onChange={(e) => setTelegramBotToken(e.target.value)}
                        placeholder={
                          database.has_telegram_bot_token
                            ? 'Dejar en blanco para mantener el actual'
                            : 'Opcional. Se cifra de forma segura'
                        }
                        disabled={!telegramEnabled}
                      />
                      <button
                        type="button"
                        className="input-eye-btn"
                        onClick={() => setShowTelegramToken((prev) => !prev)}
                        title={showTelegramToken ? 'Ocultar token' : 'Mostrar token'}
                        tabIndex={-1}
                      >
                        {showTelegramToken ? '🙈' : '👁️'}
                      </button>
                    </div>
                    <small>Opcional. Si lo dejas vacío, se usa el bot predeterminado del sistema.</small>
                  </label>

                  <div>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text)', display: 'block', marginBottom: '4px' }}>
                      Eventos a notificar:
                    </span>
                    <div className="event-chips">
                      <button
                        type="button"
                        className={`event-chip${notifyCritical ? ' event-chip--active-critical' : ''}`}
                        onClick={() => telegramEnabled && setNotifyCritical((prev) => !prev)}
                        disabled={!telegramEnabled}
                        style={{ opacity: telegramEnabled ? 1 : 0.6 }}
                        title="Alertar ante caída de base de datos o estado crítico"
                      >
                        <span>{notifyCritical ? '✓' : '+'}</span>
                        <span>🚨 Crítico y caídas</span>
                      </button>

                      <button
                        type="button"
                        className={`event-chip${notifyWarning ? ' event-chip--active-warning' : ''}`}
                        onClick={() => telegramEnabled && setNotifyWarning((prev) => !prev)}
                        disabled={!telegramEnabled}
                        style={{ opacity: telegramEnabled ? 1 : 0.6 }}
                        title="Alertar cuando se supere un umbral de advertencia"
                      >
                        <span>{notifyWarning ? '✓' : '+'}</span>
                        <span>⚠️ Advertencias</span>
                      </button>

                      <button
                        type="button"
                        className={`event-chip${notifyRecovery ? ' event-chip--active-recovery' : ''}`}
                        onClick={() => telegramEnabled && setNotifyRecovery((prev) => !prev)}
                        disabled={!telegramEnabled}
                        style={{ opacity: telegramEnabled ? 1 : 0.6 }}
                        title="Alertar cuando la base de datos vuelva al estado saludable"
                      >
                        <span>{notifyRecovery ? '✓' : '+'}</span>
                        <span>✅ Recuperación</span>
                      </button>
                    </div>
                  </div>

                  <div className="channel-card__footer" style={{ margin: '8px -20px -20px -20px' }}>
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
              </div>

              {/* Tarjeta de GitHub Issues */}
              <div className={`channel-card${githubIssuesEnabled ? ' channel-card--active' : ''}`}>
                <div className="channel-card__header">
                  <div className="channel-card__brand">
                    <div className="channel-card__icon channel-card__icon--github" aria-hidden="true">
                      🐙
                    </div>
                    <div className="channel-card__title">
                      <h3 style={{ margin: 0, fontSize: '15px' }}>Incidentes Automáticos en GitHub Issues</h3>
                      <small>Apertura automatizada de tickets</small>
                    </div>
                  </div>

                  <div className="channel-card__controls">
                    {githubIssuesEnabled && githubRepository.trim() ? (
                      <span className="badge-pill badge-pill--success">🟢 Conectado</span>
                    ) : githubIssuesEnabled ? (
                      <span className="badge-pill badge-pill--warning">⚠️ Falta Repo</span>
                    ) : (
                      <span className="badge-pill badge-pill--muted">⚪ Inactivo</span>
                    )}

                    <label className="toggle-switch" title={githubIssuesEnabled ? 'Desactivar GitHub Issues' : 'Activar GitHub Issues'}>
                      <input
                        type="checkbox"
                        id="github-issues-enabled"
                        checked={githubIssuesEnabled}
                        onChange={(e) => setGithubIssuesEnabled(e.target.checked)}
                      />
                      <span className="toggle-slider" aria-hidden="true"></span>
                    </label>
                  </div>
                </div>

                <form className="channel-card__body" onSubmit={saveGithubSettings}>
                  {githubSuccess && <SuccessNotice message={githubSuccess} />}
                  {githubError && <ErrorNotice message={githubError} />}

                  {lastGithubIssueUrl && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '6px' }}>
                      <span style={{ fontSize: '13px', color: '#a7f3d0' }}>
                        🎉 Issue creado: <strong>#{lastGithubIssueNumber ?? 'nuevo'}</strong>
                      </span>
                      <a
                        href={lastGithubIssueUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="button button--secondary"
                        style={{ padding: '4px 10px', fontSize: '12px', textDecoration: 'none' }}
                      >
                        🌐 Ver en GitHub ↗
                      </a>
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <button
                      type="button"
                      className="text-action"
                      style={{ fontSize: '0.82rem', fontWeight: 600 }}
                      onClick={() => setShowGithubGuide((prev) => !prev)}
                    >
                      {showGithubGuide ? '✕ Ocultar guía' : '💡 ¿Cómo configurar GitHub?'}
                    </button>
                    <a
                      href="https://github.com/settings/tokens/new?scopes=repo&description=DBHealthMonitor"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-action"
                      style={{ fontSize: '0.82rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      title="Crear un Personal Access Token en GitHub con scope repo"
                    >
                      ↗️ Generar Token en GitHub
                    </a>
                  </div>

                  {showGithubGuide && (
                    <div className="security-box" style={{ margin: 0 }}>
                      <strong>🐙 Cómo reportar incidentes en GitHub en 3 pasos:</strong>
                      <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                        <li>
                          <strong>1. Repositorio de destino:</strong> Indica tu repositorio en formato <code>usuario/repositorio</code> (ej: <code>mi-usuario/mi-proyecto</code>).
                        </li>
                        <li>
                          <strong>2. Token de acceso (Personal Access Token):</strong> Genera un token en GitHub con permisos de escritura en <strong>Issues</strong> (<code>repo</code> o <code>Issues: Read and Write</code>).
                        </li>
                        <li>
                          <strong>3. Seguridad garantizada:</strong> Tu token se almacena cifrado con AES-256 en la base de datos y nunca se expone en respuestas de la API.
                        </li>
                      </ul>
                    </div>
                  )}

                  <label className="field">
                    <span>Repositorio de GitHub (owner/repo)</span>
                    <input
                      type="text"
                      value={githubRepository}
                      onChange={(e) => setGithubRepository(e.target.value)}
                      placeholder="Ej: mi-usuario/mi-bd-incidentes"
                      disabled={!githubIssuesEnabled}
                    />
                    <small>Repositorio donde se crearán los tickets ante alertas críticas.</small>
                  </label>

                  <label className="field">
                    <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>
                        GitHub Personal Access Token{' '}
                        {database.has_github_token && (
                          <span style={{ color: '#6ee7b7', fontSize: '11px', fontWeight: 'bold' }}>
                            (Token guardado ✓)
                          </span>
                        )}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>🛡️ Cifrado AES-256</span>
                    </span>
                    <div className="input-eye-wrapper">
                      <input
                        type={showGithubToken ? 'text' : 'password'}
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        placeholder={
                          database.has_github_token
                            ? 'Dejar en blanco para mantener el actual'
                            : 'ghp_... (Se cifra de forma segura)'
                        }
                        disabled={!githubIssuesEnabled}
                      />
                      <button
                        type="button"
                        className="input-eye-btn"
                        onClick={() => setShowGithubToken((prev) => !prev)}
                        title={showGithubToken ? 'Ocultar token' : 'Mostrar token'}
                        tabIndex={-1}
                      >
                        {showGithubToken ? '🙈' : '👁️'}
                      </button>
                    </div>
                    <small>Opcional si usas el token global del servidor. Permiso requerido: Issues.</small>
                  </label>



                  <div className="channel-card__footer" style={{ margin: '8px -20px -20px -20px' }}>
                    <Button type="submit" busy={busyAction === 'save-github'}>
                      Guardar configuración de GitHub
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      busy={busyAction === 'test-github'}
                      disabled={!githubIssuesEnabled && !database.github_issues_enabled}
                      onClick={() => void testGithubIssue()}
                    >
                      🐙 Probar creación de Issue en GitHub
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          </section>

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
                        <td>{sample.collection_succeeded ? `${sample.metrics.length} valores` : (sample.error_message || 'Error de conexión protegido')}</td>
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
