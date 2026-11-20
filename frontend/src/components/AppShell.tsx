import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { readAccessToken } from '../core/token-store'
import { Button } from './ui'

const navigation = [
  { to: '/', label: 'Dashboard', glyph: '▦' },
  { to: '/databases', label: 'Bases de datos', glyph: '◆' },
  { to: '/docs', label: 'Documentación', glyph: '📖' },
  { to: '/thresholds', label: 'Configuración', glyph: '⚙' },
  { to: '/alerts', label: 'Alertas', glyph: '!' },
]

export function AppShell() {
  const { user, logout } = useAuth()
  const [showTokenModal, setShowTokenModal] = useState(false)
  const [tokenCopied, setTokenCopied] = useState(false)

  const activeToken = readAccessToken() || ''

  function handleCopyToken() {
    if (!activeToken) return
    navigator.clipboard.writeText(activeToken)
    setTokenCopied(true)
    setTimeout(() => setTokenCopied(false), 2500)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand" aria-label="DB Health Monitor, inicio">
          <img src="/logo.svg" alt="" width="42" height="42" />
          <span>
            <strong>DB Health</strong>
            <small>Monitor V1.0</small>
          </span>
        </NavLink>

        <nav className="sidebar__nav" aria-label="Navegación principal">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
            >
              <span className="nav-item__glyph" aria-hidden="true">{item.glyph}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <div className="account-summary">
            <span className="account-summary__avatar" aria-hidden="true">
              {user?.email.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{user?.email}</strong>
              <small>Sesión protegida</small>
              <button
                type="button"
                className="text-action"
                style={{ fontSize: '0.8rem', padding: '4px 0', display: 'block', textAlign: 'left', fontWeight: 600 }}
                onClick={() => setShowTokenModal(true)}
                title="Ver y copiar token JWT para conectar con la extensión de VS Code"
              >
                🔑 Token para VS Code
              </button>
            </span>
          </div>
          <Button variant="ghost" onClick={logout}>Cerrar sesión</Button>
        </div>
      </aside>

      <main className="main-content">
        <div className="mobile-bar">
          <NavLink to="/" className="brand" aria-label="DB Health Monitor, inicio">
            <img src="/logo.svg" alt="" width="36" height="36" />
            <strong>DB Health Monitor</strong>
          </NavLink>
          <Button variant="ghost" onClick={logout}>Salir</Button>
        </div>
        <Outlet />
      </main>

      <nav className="mobile-nav" aria-label="Navegación móvil">
        {navigation.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => (isActive ? 'mobile-nav__active' : '')}
          >
            <span aria-hidden="true">{item.glyph}</span>
            <small>{item.label}</small>
          </NavLink>
        ))}
      </nav>

      {showTokenModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '16px'
          }}
          onClick={() => setShowTokenModal(false)}
        >
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '24px',
              maxWidth: '540px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🔑 Token de Acceso para VS Code
              </h3>
              <button
                type="button"
                onClick={() => setShowTokenModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.3rem', cursor: 'pointer', padding: '4px' }}
                aria-label="Cerrar ventana"
              >
                ✕
              </button>
            </div>

            <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              Usa este token para conectar la extensión oficial de <strong>DB Health Monitor</strong> en Visual Studio Code con tu cuenta:
            </p>

            <textarea
              readOnly
              value={activeToken}
              rows={4}
              style={{
                width: '100%',
                background: 'var(--canvas)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                color: '#10b981',
                fontFamily: 'var(--mono)',
                fontSize: '0.82rem',
                padding: '12px',
                resize: 'none',
                wordBreak: 'break-all',
                outline: 'none'
              }}
              onClick={(e) => (e.target as HTMLTextAreaElement).select()}
            />

            <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '6px', padding: '10px 14px', fontSize: '0.84rem', color: '#a7f3d0' }}>
              💡 <strong>Instrucciones:</strong> En VS Code abre el panel lateral <em>DB Health Monitor</em> ➔ haz clic en <em>🔑 Conectar con Token</em> ➔ pega este código con <code>Ctrl + V</code>.
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '6px' }}>
              <Button variant="secondary" onClick={() => setShowTokenModal(false)}>
                Cerrar
              </Button>
              <Button variant="primary" onClick={handleCopyToken}>
                {tokenCopied ? '✅ ¡Copiado!' : '📋 Copiar Token'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
