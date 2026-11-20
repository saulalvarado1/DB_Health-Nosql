import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { databasesApi } from '../api/resources'
import { DatabaseCreatePage } from './DatabaseCreatePage'

describe('DatabaseCreatePage', () => {
  it('mantiene la URI oculta y sin valor predeterminado', () => {
    render(
      <MemoryRouter>
        <DatabaseCreatePage />
      </MemoryRouter>,
    )

    const uriInput = screen.getByLabelText('URI de conexión')
    expect(uriInput).toHaveAttribute('type', 'password')
    expect(uriInput).toHaveValue('')
    expect(screen.queryByDisplayValue(/secret|password|contraseña real/i)).not.toBeInTheDocument()
  })

  it('muestra advertencia cuando se detecta una dirección local o privada', () => {
    render(
      <MemoryRouter>
        <DatabaseCreatePage />
      </MemoryRouter>,
    )

    const uriInput = screen.getByLabelText('URI de conexión')
    expect(screen.queryByText(/Detección de dirección local o privada/i)).not.toBeInTheDocument()

    fireEvent.change(uriInput, { target: { value: 'redis://localhost:6379' } })
    expect(screen.getByText(/Detección de dirección local o privada/i)).toBeInTheDocument()
    expect(screen.getAllByText(/ngrok tcp 6379/i).length).toBeGreaterThanOrEqual(1)

    fireEvent.change(uriInput, { target: { value: 'redis://192.168.0.111:6379' } })
    expect(screen.getByText(/Detección de dirección local o privada/i)).toBeInTheDocument()
  })

  it('permite probar la conexión antes de registrar la instancia', async () => {
    const testSpy = vi.spyOn(databasesApi, 'testConnection').mockResolvedValue({
      success: true,
      message: 'Conexión exitosa con Redis (12 ms).',
      latency_ms: 12,
    })

    render(
      <MemoryRouter>
        <DatabaseCreatePage />
      </MemoryRouter>,
    )

    const uriInput = screen.getByLabelText('URI de conexión')
    fireEvent.change(uriInput, { target: { value: 'redis://user:pass@redis.example.com:6379/0' } })

    const testButton = screen.getByRole('button', { name: /Probar conexión/i })
    fireEvent.click(testButton)

    expect(testSpy).toHaveBeenCalledWith({
      engine: 'redis',
      connection_uri: 'redis://user:pass@redis.example.com:6379/0',
    })
    expect(await screen.findByText(/Conexión exitosa con Redis \(12 ms\)/i)).toBeInTheDocument()
  })
})
