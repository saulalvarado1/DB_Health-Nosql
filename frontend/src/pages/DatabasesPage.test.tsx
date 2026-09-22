import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MonitoredDatabase } from '../api/contracts'
import { databasesApi } from '../api/resources'
import { DatabasesPage } from './DatabasesPage'

const database: MonitoredDatabase = {
  id: 'database-1',
  name: 'Redis local de prueba',
  engine: 'redis',
  interval_seconds: 30,
  is_enabled: true,
  created_at: '2026-09-22T03:17:35Z',
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/databases']}>
      <Routes>
        <Route path="/databases" element={<DatabasesPage />} />
        <Route path="/databases/:databaseId" element={<h1>Detalle de instancia</h1>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DatabasesPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('abre el detalle al pulsar cualquier celda informativa de la fila', async () => {
    vi.spyOn(databasesApi, 'list').mockResolvedValue([database])
    const user = userEvent.setup()
    renderPage()

    const databaseLink = await screen.findByRole('link', { name: database.name })
    const row = databaseLink.closest('tr')
    expect(row).not.toBeNull()

    await user.click(within(row as HTMLTableRowElement).getByText('30s'))

    expect(await screen.findByRole('heading', { name: 'Detalle de instancia' })).toBeInTheDocument()
  })

  it('mantiene Pausar como acción independiente sin abrir el detalle', async () => {
    vi.spyOn(databasesApi, 'list').mockResolvedValue([database])
    const update = vi.spyOn(databasesApi, 'update').mockResolvedValue({
      ...database,
      is_enabled: false,
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Pausar' }))

    expect(update).toHaveBeenCalledWith(database.id, { is_enabled: false })
    expect(screen.getByRole('heading', { name: 'Bases monitorizadas' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Detalle de instancia' })).not.toBeInTheDocument()
  })

  it('mantiene Eliminar como acción independiente sin abrir el detalle', async () => {
    vi.spyOn(databasesApi, 'list').mockResolvedValue([database])
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Eliminar' }))

    expect(confirm).toHaveBeenCalledOnce()
    expect(screen.getByRole('heading', { name: 'Bases monitorizadas' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Detalle de instancia' })).not.toBeInTheDocument()
  })
})
