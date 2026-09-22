import type { AlertStatus, HealthStatus } from '../api/contracts'

const dateFormatter = new Intl.DateTimeFormat('es-PE', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const dateWithSecondsFormatter = new Intl.DateTimeFormat('es-PE', {
  dateStyle: 'medium',
  timeStyle: 'medium',
})

const timeWithSecondsFormatter = new Intl.DateTimeFormat('es-PE', {
  timeStyle: 'medium',
})

const numberFormatter = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 })

export function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : dateFormatter.format(date)
}

export function formatDateWithSeconds(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : dateWithSecondsFormatter.format(date)
}

export function formatTimeWithSeconds(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Hora no disponible' : timeWithSecondsFormatter.format(date)
}

export function formatMetric(value: number, unit: string): string {
  if (unit === 'boolean') return value > 0 ? 'Disponible' : 'No disponible'
  if (unit === 'clients') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'cliente' : 'clientes'}`
  }
  return `${numberFormatter.format(value)}${unit === 'percent' ? '%' : unit ? ` ${unit}` : ''}`
}

export const healthLabels: Record<HealthStatus, string> = {
  healthy: 'Saludable',
  warning: 'Advertencia',
  critical: 'Crítico',
  unknown: 'Sin datos',
}

export const alertStatusLabels: Record<AlertStatus, string> = {
  open: 'Abierta',
  acknowledged: 'Reconocida',
  resolved: 'Resuelta',
}
