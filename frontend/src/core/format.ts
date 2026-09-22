import type { AlertStatus, HealthStatus, MetricDiagnosticBasis } from '../api/contracts'

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

function formatBytes(value: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let normalizedValue = Math.max(0, value)
  let unitIndex = 0

  while (normalizedValue >= 1024 && unitIndex < units.length - 1) {
    normalizedValue /= 1024
    unitIndex += 1
  }

  return `${numberFormatter.format(normalizedValue)} ${units[unitIndex]}`
}

function formatDuration(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value))
  if (totalSeconds < 60) return `${totalSeconds} s`

  const totalMinutes = Math.floor(totalSeconds / 60)
  if (totalMinutes < 60) return `${totalMinutes} min`

  const totalHours = Math.floor(totalMinutes / 60)
  if (totalHours < 24) {
    const minutes = totalMinutes % 60
    return minutes ? `${totalHours} h ${minutes} min` : `${totalHours} h`
  }

  const days = Math.floor(totalHours / 24)
  const hours = totalHours % 24
  return hours ? `${days} d ${hours} h` : `${days} d`
}

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
  if (unit === 'success_boolean') return value > 0 ? 'Correcto' : 'Con error'
  if (unit === 'loading_boolean') return value > 0 ? 'En carga' : 'Operativa'
  if (unit === 'bytes') return formatBytes(value)
  if (unit === 'seconds') return formatDuration(value)
  if (unit === 'microseconds') return `${numberFormatter.format(value)} µs`
  if (unit === 'kilobytes/second') return `${numberFormatter.format(value)} KB/s`
  if (unit === 'ratio') return `${numberFormatter.format(value)}×`
  if (unit === 'clients') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'cliente' : 'clientes'}`
  }
  if (unit === 'connections') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'conexión' : 'conexiones'}`
  }
  if (unit === 'keys') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'clave' : 'claves'}`
  }
  if (unit === 'cursors') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'cursor' : 'cursores'}`
  }
  if (unit === 'documents') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'documento' : 'documentos'}`
  }
  if (unit === 'requests') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'solicitud' : 'solicitudes'}`
  }
  if (unit === 'channels') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'canal' : 'canales'}`
  }
  if (unit === 'replicas') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'réplica' : 'réplicas'}`
  }
  if (unit === 'operations') {
    return `${numberFormatter.format(value)} ${value === 1 ? 'operación' : 'operaciones'}`
  }
  if (unit === 'operations/second') return `${numberFormatter.format(value)} op/s`
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

export const diagnosticBasisLabels: Record<MetricDiagnosticBasis, string> = {
  threshold: 'Según umbral configurado',
  heuristic: 'Diagnóstico orientativo',
  informational: 'Dato contextual',
}
