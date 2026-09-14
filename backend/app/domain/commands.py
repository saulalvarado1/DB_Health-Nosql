from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RegisterMonitoredDatabaseCommand:
    name: str
    engine_id: str
    connection_uri: str
    interval_seconds: int
