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

  it('convierte bytes y segundos a unidades legibles', () => {
    expect(formatMetric(1_536, 'bytes')).toBe('1.5 KB')
    expect(formatMetric(3_661, 'seconds')).toBe('1 h 1 min')
  })

  it('presenta las unidades operativas sin exponer códigos internos', () => {
    expect(formatMetric(1, 'connections')).toBe('1 conexión')
    expect(formatMetric(2, 'keys')).toBe('2 claves')
    expect(formatMetric(3, 'operations/second')).toBe('3 op/s')
    expect(formatMetric(1.25, 'ratio')).toBe('1.25×')
    expect(formatMetric(4, 'cursors')).toBe('4 cursores')
    expect(formatMetric(8, 'documents')).toBe('8 documentos')
    expect(formatMetric(250, 'microseconds')).toBe('250 µs')
    expect(formatMetric(1.5, 'kilobytes/second')).toBe('1.5 KB/s')
    expect(formatMetric(1, 'success_boolean')).toBe('Correcto')
    expect(formatMetric(0, 'loading_boolean')).toBe('Operativa')
  })
})
