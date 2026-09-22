import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { Button, ErrorNotice } from '../components/ui'
import { getErrorMessage } from '../core/errors'

type AuthMode = 'login' | 'register'

export function AuthPage() {
  const { user, login, register } = useAuth()
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (mode === 'register' && password.length < 12) {
      setError('La contraseña debe tener al menos 12 caracteres.')
      return
    }

    setBusy(true)
    try {
      const credentials = { email: email.trim(), password }
      if (mode === 'login') await login(credentials)
      else await register(credentials)
      setPassword('')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode)
    setError('')
    setPassword('')
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-brand">
          <img src="/logo.svg" alt="" width="52" height="52" />
          <span>
            <strong>DB Health Monitor</strong>
            <small>Monitoreo MongoDB y Redis</small>
          </span>
        </div>

        <div className="auth-tabs" role="tablist" aria-label="Tipo de acceso">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'auth-tabs__active' : ''}
            onClick={() => changeMode('login')}
          >
            Iniciar sesión
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'auth-tabs__active' : ''}
            onClick={() => changeMode('register')}
          >
            Crear cuenta
          </button>
        </div>

        <div className="auth-card__intro">
          <span className="eyebrow">Acceso seguro</span>
          <h1 id="auth-title">{mode === 'login' ? 'Bienvenido nuevamente' : 'Crea tu cuenta'}</h1>
          <p>
            {mode === 'login'
              ? 'Ingresa con las credenciales de tu plataforma.'
              : 'La cuenta solo tendrá acceso a sus propias instancias monitorizadas.'}
          </p>
        </div>

        <form className="form-stack" onSubmit={handleSubmit}>
          {error && <ErrorNotice message={error} />}
          <label className="field">
            <span>Correo electrónico</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
              maxLength={320}
              placeholder="usuario@ejemplo.com"
            />
          </label>
          <label className="field">
            <span>Contraseña</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              minLength={mode === 'register' ? 12 : 1}
              maxLength={128}
            />
            {mode === 'register' && <small>Mínimo 12 caracteres.</small>}
          </label>
          <Button type="submit" busy={busy}>
            {mode === 'login' ? 'Ingresar' : 'Registrar cuenta'}
          </Button>
        </form>

        <p className="security-caption">
          La aplicación nunca solicita credenciales de MongoDB o Redis en esta pantalla.
        </p>
      </section>

      <aside className="auth-visual" aria-label="Descripción del producto">
        <div>
          <span className="eyebrow">Visibilidad operativa</span>
          <h2>La salud de tus bases NoSQL en un solo lugar.</h2>
          <p>
            Recolección de métricas de solo lectura, historial de salud, umbrales configurables y
            alertas controladas por usuario.
          </p>
        </div>
        <ul>
          <li><span>01</span> Credenciales cifradas antes de persistirse</li>
          <li><span>02</span> Aislamiento de información entre usuarios</li>
          <li><span>03</span> Conectores de privilegio mínimo</li>
        </ul>
      </aside>
    </main>
  )
}
