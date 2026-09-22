import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { Button } from './ui'

const navigation = [
  { to: '/', label: 'Dashboard', glyph: '▦' },
  { to: '/databases', label: 'Bases de datos', glyph: '◆' },
  { to: '/thresholds', label: 'Umbrales', glyph: '⌁' },
  { to: '/alerts', label: 'Alertas', glyph: '!' },
]

export function AppShell() {
  const { user, logout } = useAuth()

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
    </div>
  )
}
