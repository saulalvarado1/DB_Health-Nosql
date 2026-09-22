import type { ButtonHTMLAttributes, PropsWithChildren, ReactNode } from 'react'

import type { AlertSeverity, AlertStatus, HealthStatus } from '../api/contracts'
import { alertStatusLabels, healthLabels } from '../core/format'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  busy?: boolean
}

export function Button({
  variant = 'primary',
  busy = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`button button--${variant}`}
      disabled={disabled || busy}
      aria-busy={busy}
      {...props}
    >
      {busy ? 'Procesando…' : children}
    </button>
  )
}

interface PanelProps extends PropsWithChildren {
  title?: string
  description?: string
  action?: ReactNode
  className?: string
}

export function Panel({ title, description, action, className = '', children }: PanelProps) {
  return (
    <section className={`panel ${className}`.trim()}>
      {(title || description || action) && (
        <header className="panel__header">
          <div>
            {title && <h2>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

type BadgeStatus = HealthStatus | AlertStatus | AlertSeverity | 'enabled' | 'disabled'

const badgeLabels: Record<BadgeStatus, string> = {
  ...healthLabels,
  ...alertStatusLabels,
  warning: 'Advertencia',
  critical: 'Crítica',
  enabled: 'Activa',
  disabled: 'Pausada',
}

export function StatusBadge({ status }: { status: BadgeStatus }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      <span aria-hidden="true" />
      {badgeLabels[status]}
    </span>
  )
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="notice notice--error" role="alert">
      {message}
    </div>
  )
}

export function SuccessNotice({ message }: { message: string }) {
  return (
    <div className="notice notice--success" role="status">
      {message}
    </div>
  )
}

export function LoadingState({ label = 'Cargando información…' }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  )
}

export function EmptyState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon" aria-hidden="true">◇</div>
      <h3>{title}</h3>
      <p>{message}</p>
      {action}
    </div>
  )
}

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="page-heading__action">{action}</div>}
    </header>
  )
}
