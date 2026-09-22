import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import type { MonitoredDatabase, ThresholdProfile, ThresholdRule } from '../api/contracts'
import { databasesApi } from '../api/resources'
import { Button, EmptyState, ErrorNotice, LoadingState, PageHeading, Panel, SuccessNotice } from '../components/ui'
import { getErrorMessage } from '../core/errors'

function RuleEditor({
  databaseId,
  rule,
  onSaved,
}: {
  databaseId: string
  rule: ThresholdRule
  onSaved: (profile: ThresholdProfile) => void
}) {
  const [warningValue, setWarningValue] = useState(rule.warning_value)
  const [criticalValue, setCriticalValue] = useState(rule.critical_value)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSaved(false)

    const isValid = rule.alert_direction === 'above'
      ? warningValue < criticalValue
      : warningValue > criticalValue
    if (!isValid) {
      setError(
        rule.alert_direction === 'above'
          ? 'En una métrica ascendente, advertencia debe ser menor que crítica.'
          : 'En una métrica descendente, advertencia debe ser mayor que crítica.',
      )
      return
    }

    setBusy(true)
    try {
      onSaved(
        await databasesApi.updateThreshold(databaseId, rule.metric_code, {
          warning_value: warningValue,
          critical_value: criticalValue,
        }),
      )
      setSaved(true)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="threshold-rule" onSubmit={handleSubmit}>
      <div className="threshold-rule__heading">
        <div><strong>{rule.display_name}</strong><code>{rule.metric_code}</code></div>
        <span>Alerta cuando está {rule.alert_direction === 'above' ? 'por encima' : 'por debajo'}</span>
      </div>
      <label className="field"><span>Advertencia ({rule.unit})</span><input type="number" step="any" value={warningValue} onChange={(event) => setWarningValue(event.target.valueAsNumber)} required /></label>
      <label className="field"><span>Crítica ({rule.unit})</span><input type="number" step="any" value={criticalValue} onChange={(event) => setCriticalValue(event.target.valueAsNumber)} required /></label>
      <Button type="submit" variant="secondary" busy={busy}>Guardar regla</Button>
      {error && <div className="threshold-rule__message"><ErrorNotice message={error} /></div>}
      {saved && <div className="threshold-rule__message"><SuccessNotice message="Regla guardada." /></div>}
    </form>
  )
}

export function ThresholdsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [databases, setDatabases] = useState<MonitoredDatabase[]>([])
  const [profile, setProfile] = useState<ThresholdProfile | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const selectedId = searchParams.get('database') ?? ''

  useEffect(() => {
    let active = true
    databasesApi.list()
      .then((response) => {
        if (!active) return
      setDatabases(response)
      if (response.length > 0 && !response.some((database) => database.id === selectedId)) {
        const first = response[0]
        if (first) setSearchParams({ database: first.id }, { replace: true })
      }
      })
      .catch((requestError: unknown) => {
        if (active) setError(getErrorMessage(requestError))
      })
      .finally(() => {
        if (active && !selectedId) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [selectedId, setSearchParams])

  useEffect(() => {
    if (!selectedId) {
      return
    }
    let active = true
    async function loadProfile() {
      await Promise.resolve()
      if (!active) return
      setLoading(true)
      setError('')
      try {
        const response = await databasesApi.thresholds(selectedId)
        if (active) setProfile(response)
      } catch (requestError) {
        if (active) setError(getErrorMessage(requestError))
      } finally {
        if (active) setLoading(false)
      }
    }
    void loadProfile()
    return () => {
      active = false
    }
  }, [selectedId])

  return (
    <div className="page">
      <PageHeading
        eyebrow="Evaluación de salud"
        title="Umbrales"
        description="Las reglas se administran por instancia y solo para métricas soportadas por su motor."
      />

      {error && <ErrorNotice message={error} />}

      <Panel>
        <label className="field threshold-selector">
          <span>Instancia monitorizada</span>
          <select
            value={selectedId}
            onChange={(event) => setSearchParams({ database: event.target.value })}
            disabled={!databases.length}
          >
            {!databases.length && <option value="">Sin instancias</option>}
            {databases.map((database) => <option key={database.id} value={database.id}>{database.name} · {database.engine}</option>)}
          </select>
        </label>
      </Panel>

      {loading ? <LoadingState /> : profile ? (
        <Panel
          title={profile.name}
          description={`${profile.engine.toUpperCase()} · ${profile.is_default ? 'perfil predeterminado' : 'perfil personalizado'}`}
        >
          <div className="threshold-list">
            {profile.rules.map((rule) => (
              <RuleEditor key={`${selectedId}:${rule.metric_code}`} databaseId={selectedId} rule={rule} onSaved={setProfile} />
            ))}
          </div>
        </Panel>
      ) : !databases.length ? (
        <EmptyState
          title="No hay instancias"
          message="Primero registra una base de datos para consultar sus umbrales."
          action={<Link className="button button--primary" to="/databases/new">Registrar instancia</Link>}
        />
      ) : null}
    </div>
  )
}
