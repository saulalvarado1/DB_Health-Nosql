import { useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { DatabaseEngine } from '../api/contracts'
import { databasesApi } from '../api/resources'
import { Button, ErrorNotice, PageHeading, Panel, SuccessNotice } from '../components/ui'
import { getErrorMessage } from '../core/errors'

export function DatabaseCreatePage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [engine, setEngine] = useState<DatabaseEngine>('redis')
  const [connectionUri, setConnectionUri] = useState('')
  const [intervalSeconds, setIntervalSeconds] = useState(30)
  const [error, setError] = useState('')
  const [testSuccess, setTestSuccess] = useState('')
  const [busy, setBusy] = useState(false)
  const [testing, setTesting] = useState(false)

  const isLocalHostAddress = useMemo(() => {
    const lower = connectionUri.toLowerCase()
    return (
      lower.includes('localhost') ||
      lower.includes('127.0.0.1') ||
      lower.includes('192.168.') ||
      lower.includes('10.') ||
      lower.includes('172.16.')
    )
  }, [connectionUri])

  async function handleTestConnection() {
    if (!connectionUri.trim()) {
      setError('Ingresa una URI de conexión antes de probar.')
      return
    }
    setError('')
    setTestSuccess('')
    setTesting(true)
    try {
      const result = await databasesApi.testConnection({
        engine,
        connection_uri: connectionUri.trim(),
      })
      setTestSuccess(`✅ ${result.message}`)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setTesting(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setTestSuccess('')
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
          {testSuccess && <div className="form-grid__full"><SuccessNotice message={testSuccess} /></div>}

          <label className="field">
            <span>Nombre de la instancia</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              required
              placeholder={engine === 'redis' ? 'Ej: Redis de producción' : 'Ej: MongoDB Atlas o Cluster0'}
            />
          </label>

          <label className="field">
            <span>Motor</span>
            <select
              value={engine}
              onChange={(event) => {
                setEngine(event.target.value as DatabaseEngine)
                setTestSuccess('')
                setError('')
              }}
            >
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
              onChange={(event) => {
                setConnectionUri(event.target.value)
                setTestSuccess('')
                setError('')
              }}
              autoComplete="new-password"
              spellCheck={false}
              required
              placeholder={engine === 'redis' ? 'redis://usuario:contraseña@host:6379/0' : 'mongodb://usuario:contraseña@host:27017/?authSource=admin'}
            />
            <small>Se verifica la conectividad real antes de guardar y se cifra con AES-256 antes de persistirse. No se puede recuperar posteriormente.</small>
          </label>

          {isLocalHostAddress && (
            <div className="security-box security-box--warning form-grid__full">
              <strong>⚠️ Detección de dirección local o privada</strong>
              <p>
                Has ingresado una dirección de red local o privada. Si estás utilizando esta plataforma desde la nube (VPS), los servidores externos no pueden acceder a tu red privada sin un puente de red.
              </p>
              <p>
                Para monitorear tu base de datos local desde la nube, crea un túnel TCP seguro con herramientas como ngrok (ejemplo: <code>ngrok tcp {engine === 'redis' ? '6379' : '27017'}</code>) e ingresa la URL pública proporcionada, o ejecuta DB Health Monitor en tu entorno local.
              </p>
            </div>
          )}

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

          <div className="form-actions form-grid__full">
            <Link className="button button--secondary" to="/databases">Cancelar</Link>
            <Button
              type="button"
              variant="secondary"
              busy={testing}
              disabled={!connectionUri.trim() || busy}
              onClick={() => void handleTestConnection()}
            >
              🔌 Probar conexión
            </Button>
            <Button type="submit" busy={busy} disabled={testing}>
              Verificar y guardar
            </Button>
          </div>
        </form>
      </Panel>
    </div>
  )
}
