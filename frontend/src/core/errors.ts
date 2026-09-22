import { ApiError } from '../api/http-client'

export function getErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Ocurrió un error inesperado.'
}
