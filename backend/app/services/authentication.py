from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.domain.commands import RegisterUserCommand
from app.domain.errors import AuthenticationError, ResourceConflictError
from app.infrastructure.persistence.models import User
from app.infrastructure.repositories.thresholds import ThresholdProfileRepository
from app.infrastructure.repositories.users import UserRepository


class AuthenticationService:
    """Casos de uso de registro y autenticación, sin conocer HTTP."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)

    def register(self, command: RegisterUserCommand) -> User:
        normalized_email = command.email.strip().lower()
        if self._users.get_by_email(normalized_email) is not None:
            raise ResourceConflictError("Ya existe una cuenta con ese correo.")

        user = User(email=normalized_email, password_hash=hash_password(command.password))
        self._users.add(user)
        try:
            self._session.flush()
            ThresholdProfileRepository(self._session).create_defaults_for_user(user.id)
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise ResourceConflictError("Ya existe una cuenta con ese correo.") from error
        self._session.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self._users.get_by_email(email.strip().lower())
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError("Correo o contraseña incorrectos.")
        return user
