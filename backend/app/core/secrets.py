from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.domain.errors import ServiceUnavailableError


class CredentialsCipher:
    """Cifra secretos de conexión antes de guardarlos en PostgreSQL."""

    def __init__(self, encryption_key: str | None = None) -> None:
        key = encryption_key or (
            settings.credentials_encryption_key.get_secret_value()
            if settings.credentials_encryption_key
            else None
        )
        if not key:
            raise ServiceUnavailableError("El cifrado de credenciales no está configurado.")
        try:
            self._fernet = Fernet(key.encode())
        except (TypeError, ValueError) as error:
            raise ServiceUnavailableError(
                "La configuración de cifrado de credenciales no es válida."
            ) from error

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_value.encode()).decode()
        except InvalidToken as error:
            raise ValueError("No se pudo descifrar la credencial almacenada.") from error
