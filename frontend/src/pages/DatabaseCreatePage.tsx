import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { DatabaseEngine } from '../api/contracts'
import { databasesApi } from '../api/resources'
import { Button, ErrorNotice, PageHeading, Panel } from '../components/ui'
import { getErrorMessage } from '../core/errors'

export function DatabaseCreatePage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [engine, setEngine] = useState<DatabaseEngine>('redis')
  const [connectionUri, setConnectionUri] = useState('')
  const [intervalSeconds, setIntervalSeconds] = useState(30)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const database = await databasesApi.create({
        name: name.trim(),
        engine,
        connection_uri: connectionUri.trim(),
        interval_seconds: intervalSeconds,
      })
      setConnectionUri('')
      navigate(`/databases/${database.id}`, { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page page--narrow">
      <PageHeading
        eyebrow="Nueva conexión"
        title="Registrar instancia"
        description="Utiliza un usuario de monitoreo con los permisos mínimos indicados para cada motor."
        action={<Link className="button button--secondary" to="/databases">Cancelar</Link>}
      />

      <Panel>
        <form className="form-grid" onSubmit={handleSubmit}>
          {error && <div className="form-grid__full"><ErrorNotice message={error} /></div>}

          <label className="field">
            <span>Nombre de la instancia</span>
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required placeholder="Redis de producción" />
          </label>

          <label className="field">
            <span>Motor</span>
            <select value={engine} onChange={(event) => setEngine(event.target.value as DatabaseEngine)}>
              <option value="redis">Redis</option>
              <option value="mongodb">MongoDB</option>
            </select>
          </label>

          <label className="field form-grid__full">
            <span>URI de conexión</span>
            <input
              type="password"
              aria-label="URI de conexión"
              value={connectionUri}
              onChange={(event) => setConnectionUri(event.target.value)}
              autoComplete="new-password"
              spellCheck={false}
              required
              placeholder={engine === 'redis' ? 'redis://usuario:contraseña@host:6379/0' : 'mongodb://usuario:contraseña@host:27017/?authSource=admin'}
            />
            <small>Se transmite a la API y se cifra antes de persistirse. No se puede recuperar posteriormente.</small>
          </label>

          <label className="field">
            <span>Intervalo de monitoreo</span>
            <div className="input-with-suffix">
              <input
                type="number"
                value={intervalSeconds}
                onChange={(event) => setIntervalSeconds(event.target.valueAsNumber)}
                min={10}
                max={86_400}
                required
              />
              <span>segundos</span>
            </div>
            <small>Permitido: entre 10 segundos y 24 horas.</small>
          </label>

          <div className="security-box form-grid__full">
            <strong>Antes de continuar</strong>
            <p>
              La cuenta remota debe permitir únicamente las operaciones de lectura necesarias para métricas. El monitor no necesita escribir datos en Redis ni MongoDB.
            </p>
          </div>

          <div className="form-actions form-grid__full">
            <Link className="button button--secondary" to="/databases">Cancelar</Link>
            <Button type="submit" busy={busy}>Guardar y comenzar monitoreo</Button>
          </div>
        </form>
      </Panel>
    </div>
  )
}
