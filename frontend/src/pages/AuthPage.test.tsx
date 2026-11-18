import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthContext } from '../auth/context'
import { AuthPage } from './AuthPage'

function renderAuthPage(authOverrides = {}) {
  const defaultAuth = {
    user: null,
    isInitializing: false,
    login: vi.fn(),
    register: vi.fn(),
    loginWithGoogle: vi.fn(),
    logout: vi.fn(),
    ...authOverrides,
  }

  return {
    ...render(
      <MemoryRouter>
        <AuthContext.Provider value={defaultAuth}>
          <AuthPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    ),
    auth: defaultAuth,
  }
}

describe('AuthPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renderiza el botón de Continuar con Google y el formulario de acceso', () => {
    renderAuthPage()

    expect(screen.getByRole('button', { name: /continuar con google/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
  })

  it('permite alternar entre Iniciar sesión y Crear cuenta', async () => {
    const user = userEvent.setup()
    renderAuthPage()

    const registerTab = screen.getByRole('tab', { name: /crear cuenta/i })
    await user.click(registerTab)

    expect(screen.getByRole('heading', { name: /crea tu cuenta/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /registrar cuenta/i })).toBeInTheDocument()
  })

  it('invoca loginWithGoogle cuando el usuario ingresa un token en el prompt de prueba', async () => {
    const user = userEvent.setup()
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('mock-google-id-token-123')
    const { auth } = renderAuthPage()

    const googleBtn = screen.getByRole('button', { name: /continuar con google/i })
    await user.click(googleBtn)

    expect(promptSpy).toHaveBeenCalled()
    expect(auth.loginWithGoogle).toHaveBeenCalledWith('mock-google-id-token-123')
  })
})
