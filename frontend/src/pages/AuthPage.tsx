import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { Button, ErrorNotice } from '../components/ui'
import { GOOGLE_CLIENT_ID } from '../core/environment'
import { getErrorMessage } from '../core/errors'

type AuthMode = 'login' | 'register'

interface GoogleCredentialResponse {
  credential?: string
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: GoogleCredentialResponse) => void
          }) => void
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void
          prompt: () => void
        }
      }
    }
  }
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3h3.88c2.27-2.09 3.66-5.17 3.66-9.09z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.1C3.28 21.44 7.33 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.32c-.25-.72-.38-1.49-.38-2.32s.13-1.6.38-2.32V6.57H1.25C.45 8.16 0 9.98 0 12s.45 3.84 1.25 5.43l4.03-3.11z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.28 2.56 1.25 6.57l4.03 3.11c.95-2.83 3.6-4.93 6.72-4.93z"
      />
    </svg>
  )
}

export function AuthPage() {
  const { user, login, register, loginWithGoogle } = useAuth()
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const googleBtnContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return

    const initGoogle = () => {
      if (!window.google?.accounts?.id || !googleBtnContainerRef.current) return
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response: GoogleCredentialResponse) => {
          if (!response.credential) return
          setBusy(true)
          setError('')
          try {
            await loginWithGoogle(response.credential)
          } catch (requestError) {
            setError(getErrorMessage(requestError))
          } finally {
            setBusy(false)
          }
        },
      })
      googleBtnContainerRef.current.innerHTML = ''
      window.google.accounts.id.renderButton(googleBtnContainerRef.current, {
        type: 'standard',
        theme: 'filled_black',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: 380,
      })
    }

    if (window.google?.accounts?.id) {
      initGoogle()
    } else {
      const timer = window.setInterval(() => {
        if (window.google?.accounts?.id) {
          initGoogle()
          window.clearInterval(timer)
        }
      }, 300)
      return () => window.clearInterval(timer)
    }
  }, [loginWithGoogle])

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

  async function handleGoogleClick() {
    setError('')
    if (GOOGLE_CLIENT_ID && window.google?.accounts?.id) {
      window.google.accounts.id.prompt()
      return
    }

    const manualToken = window.prompt(
      'Para autenticarse directamente con Google en producción, configure VITE_GOOGLE_CLIENT_ID.\n\nPara pruebas locales o desarrollo, ingrese el token/credential (JWT) de Google:'
    )
    if (!manualToken?.trim()) return

    setBusy(true)
    try {
      await loginWithGoogle(manualToken.trim())
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

        {error && <ErrorNotice message={error} />}

        {GOOGLE_CLIENT_ID && (
          <div
            ref={googleBtnContainerRef}
            className="google-button-container"
            style={{ marginBottom: '14px' }}
          />
        )}

        {!GOOGLE_CLIENT_ID && (
          <button
            type="button"
            className="google-auth-btn"
            onClick={handleGoogleClick}
            disabled={busy}
            aria-label="Continuar con Google"
          >
            <GoogleIcon />
            <span>Continuar con Google</span>
          </button>
        )}

        <div className="auth-divider">
          <span>o con correo</span>
        </div>

        <form className="form-stack" onSubmit={handleSubmit}>
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
