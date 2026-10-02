import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  MetricDiagnosticBasis,
  MetricDiagnosticStatus,
  MetricValue,
  MonitoredDatabase,
  MonitoringHistory,
} from '../api/contracts'
import { databasesApi } from '../api/resources'
import { DatabaseDetailPage } from './DatabaseDetailPage'

const database: MonitoredDatabase = {
  id: 'database-1',
  name: 'Redis local de prueba',
  engine: 'redis',
  interval_seconds: 30,
  is_enabled: false,
  created_at: '2026-09-22T03:17:35Z',
}

function metric(
  code: string,
  displayName: string,
  unit: string,
  value: number,
  status: MetricDiagnosticStatus = 'informational',
  diagnosticBasis: MetricDiagnosticBasis = 'informational',
  message = 'Necesita una línea base del entorno.',
): MetricValue {
  return {
    code,
    display_name: displayName,
    unit,
    value,
    status,
    diagnostic_basis: diagnosticBasis,
    message,
  }
}

const history: MonitoringHistory[] = [
  {
    sample_id: 'sample-1',
    collected_at: '2026-09-22T03:18:05Z',
    collection_succeeded: true,
    error_message: null,
    health_score: 100,
    health_status: 'healthy',
    evaluated_at: '2026-09-22T03:18:05Z',
    metrics: [
      metric(
        'availability',
        'Disponibilidad',
        'boolean',
        1,
        'healthy',
        'threshold',
        'Está por encima del umbral de advertencia configurado.',
      ),
      metric(
        'blocked_clients',
        'Clientes bloqueados',
        'clients',
        0,
        'healthy',
        'heuristic',
        'No hay clientes esperando operaciones bloqueantes.',
      ),
      metric('connected_clients', 'Clientes conectados', 'clients', 1),
      metric('connected_replicas', 'Réplicas conectadas', 'replicas', 0),
      metric('evicted_keys', 'Claves expulsadas', 'keys', 2, 'warning', 'heuristic', 'Se detectaron claves expulsadas.'),
      metric('expired_keys', 'Claves expiradas', 'keys', 4),
      metric('expiring_keys_total', 'Claves con expiración', 'keys', 2),
      metric('instantaneous_input_kbps', 'Entrada de red', 'kilobytes/second', 1.5),
      metric('instantaneous_output_kbps', 'Salida de red', 'kilobytes/second', 2.5),
      metric('keys_total', 'Claves almacenadas', 'keys', 12),
      metric('keyspace_hit_rate_percent', 'Aciertos de caché', 'percent', 80, 'healthy', 'heuristic'),
      metric('keyspace_hits_total', 'Aciertos acumulados', 'keys', 80),
      metric('keyspace_misses_total', 'Fallos acumulados', 'keys', 20),
      metric('latest_fork_microseconds', 'Duración del último fork', 'microseconds', 250),
      metric('loading', 'Carga de datos', 'loading_boolean', 0, 'healthy', 'heuristic'),
      metric('memory_fragmentation_ratio', 'Fragmentación de memoria', 'ratio', 1.25, 'healthy', 'heuristic'),
      metric('memory_usage_percent', 'Uso de memoria', 'percent', 25, 'healthy', 'threshold'),
      metric('network_input_bytes_total', 'Red recibida', 'bytes', 1_024),
      metric('network_output_bytes_total', 'Red enviada', 'bytes', 2_048),
      metric('operations_per_second', 'Operaciones por segundo', 'operations/second', 3),
      metric('persistence_last_save_success', 'Último guardado', 'success_boolean', 1, 'healthy', 'heuristic'),
      metric('pubsub_channels', 'Canales Pub/Sub', 'channels', 0),
      metric('rejected_connections', 'Conexiones rechazadas', 'connections', 0, 'healthy', 'heuristic'),
      metric('total_commands_processed', 'Comandos procesados', 'operations', 200),
      metric('total_connections_received', 'Conexiones recibidas', 'connections', 50),
      metric('uptime_seconds', 'Tiempo activo', 'seconds', 3_661),
      metric('used_memory_bytes', 'Memoria usada', 'bytes', 1_536),
    ],
  },
]

describe('DatabaseDetailPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra el catálogo completo de la última recolección', async () => {
    vi.spyOn(databasesApi, 'get').mockResolvedValue(database)
    vi.spyOn(databasesApi, 'history').mockResolvedValue(history)

    render(
      <MemoryRouter initialEntries={['/databases/database-1']}>
        <Routes>
          <Route path="/databases/:databaseId" element={<DatabaseDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const title = await screen.findByRole('heading', { name: 'Métricas actuales' })
    const panel = title.closest('section')
    expect(panel).not.toBeNull()

    expect(within(panel as HTMLElement).getByLabelText('Resumen de diagnósticos')).toHaveTextContent('Informativas')
    expect(within(panel as HTMLElement).getByRole('button', { name: /Datos informativos/ })).toHaveAttribute('aria-expanded', 'false')
    expect(await within(panel as HTMLElement).findByText('Claves expulsadas')).toBeInTheDocument()

    fireEvent.click(within(panel as HTMLElement).getByRole('button', { name: /Estado verificado/ }))
    fireEvent.click(within(panel as HTMLElement).getByRole('button', { name: /Datos informativos/ }))

    expect(within(panel as HTMLElement).getByText('Aciertos de caché')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('80%')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('1.25×')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('1 h 1 min')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('1.5 KB')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('250 µs')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('Correcto')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('Operativa')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getByText('No hay clientes esperando operaciones bloqueantes.')).toBeInTheDocument()
    expect(panel).toHaveTextContent('Según umbral configurado')
    expect(within(panel as HTMLElement).getByText('Advertencia')).toBeInTheDocument()
    expect(within(panel as HTMLElement).getAllByRole('article')).toHaveLength(27)
  })

  it('conserva la última muestra correcta cuando la recolección más reciente falla', async () => {
    const successfulSample = history[0]
    if (!successfulSample) throw new Error('La prueba necesita una muestra correcta.')

    vi.spyOn(databasesApi, 'get').mockResolvedValue(database)
    vi.spyOn(databasesApi, 'history').mockResolvedValue([
      {
        ...successfulSample,
        sample_id: 'sample-failed',
        collected_at: '2026-09-22T03:19:05Z',
        collection_succeeded: false,
        error_message: 'No fue posible conectar con Redis.',
        health_score: 0,
        health_status: 'critical',
        metrics: [],
      },
      successfulSample,
    ])

    render(
      <MemoryRouter initialEntries={['/databases/database-1']}>
        <Routes>
          <Route path="/databases/:databaseId" element={<DatabaseDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La última recolección no obtuvo métricas',
    )
    expect(screen.getByRole('heading', { name: 'Métricas actuales' }).parentElement).toHaveTextContent(
      'Última muestra correcta',
    )
    expect(screen.getByLabelText('Resumen de diagnósticos')).toBeInTheDocument()
  })

  it('permite filtrar el historial por rango de tiempo y actualizar la consulta', async () => {
    vi.spyOn(databasesApi, 'get').mockResolvedValue(database)
    const historySpy = vi.spyOn(databasesApi, 'history').mockResolvedValue(history)

    render(
      <MemoryRouter initialEntries={['/databases/database-1']}>
        <Routes>
          <Route path="/databases/:databaseId" element={<DatabaseDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByRole('heading', { name: 'Métricas actuales' })

    const btn1h = screen.getByRole('button', { name: '1 hora' })
    expect(btn1h).toBeInTheDocument()

    fireEvent.click(btn1h)
    expect(historySpy).toHaveBeenCalledWith('database-1', 100, '1h')
    expect(btn1h).toHaveClass('filter-tabs__active')
  })

  it('permite configurar y probar notificaciones de Telegram', async () => {
    vi.spyOn(databasesApi, 'get').mockResolvedValue({
      ...database,
      telegram_notifications_enabled: true,
      telegram_chat_id: '998877',
      has_telegram_bot_token: true,
    })
    vi.spyOn(databasesApi, 'history').mockResolvedValue(history)
    const testSpy = vi.spyOn(databasesApi, 'testTelegram').mockResolvedValue({
      success: true,
      message: 'Mensaje de prueba enviado exitosamente a Telegram.',
    })

    render(
      <MemoryRouter initialEntries={['/databases/database-1']}>
        <Routes>
          <Route path="/databases/:databaseId" element={<DatabaseDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Alertas y Notificaciones a Telegram' })).toBeInTheDocument()

    const chatIdInput = screen.getByPlaceholderText(/Ej: 123456789/i)
    expect(chatIdInput).toHaveValue('998877')

    const testBtn = screen.getByRole('button', { name: /Enviar mensaje de prueba a Telegram/i })
    expect(testBtn).toBeInTheDocument()

    fireEvent.click(testBtn)
    expect(testSpy).toHaveBeenCalledWith('database-1', {
      chat_id: '998877',
      bot_token: undefined,
    })

    expect(await screen.findByText(/Mensaje de prueba enviado exitosamente a Telegram/i)).toBeInTheDocument()
  })
})

