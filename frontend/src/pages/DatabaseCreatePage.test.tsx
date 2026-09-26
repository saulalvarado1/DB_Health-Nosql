import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

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
    expect(screen.getByText(/Guía de conectividad según el entorno/i)).toBeInTheDocument()
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
})
