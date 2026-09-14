class DomainError(Exception):
    """Error controlado que puede comunicarse de forma segura por la API."""


class ResourceNotFoundError(DomainError):
    pass


class ResourceConflictError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class ConfigurationError(DomainError):
    pass


class ServiceUnavailableError(DomainError):
    pass


class ConnectorUnavailableError(DomainError):
    pass
