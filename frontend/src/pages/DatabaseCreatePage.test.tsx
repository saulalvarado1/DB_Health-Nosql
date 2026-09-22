import { render, screen } from '@testing-library/react'
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
  })
})
