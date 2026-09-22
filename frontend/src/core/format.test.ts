import { describe, expect, it } from 'vitest'

import { formatDateWithSeconds, formatMetric, formatTimeWithSeconds } from './format'

describe('formatDateWithSeconds', () => {
  it('incluye segundos para diferenciar muestras del mismo minuto', () => {
    expect(formatDateWithSeconds('2026-09-22T03:17:35Z')).toMatch(/\d{1,2}:\d{2}:\d{2}/)
  })

  it('protege la interfaz ante fechas inválidas', () => {
    expect(formatDateWithSeconds('fecha-invalida')).toBe('Fecha no disponible')
  })

  it('muestra la hora de actualización con segundos', () => {
    expect(formatTimeWithSeconds('2026-09-22T03:17:35Z')).toMatch(/\d{1,2}:\d{2}:\d{2}/)
  })

  it('presenta correctamente clientes en singular y plural', () => {
    expect(formatMetric(1, 'clients')).toBe('1 cliente')
    expect(formatMetric(2, 'clients')).toBe('2 clientes')
  })
})
