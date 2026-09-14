"""Crea la base de datos y el rol mínimo que utilizará DB Health Monitor.

No escribe secretos ni cadenas de conexión en la salida. Ejecútalo una sola vez
con un usuario administrador de PostgreSQL y posteriormente aplica Alembic.
"""

import re
import sys

import psycopg
from psycopg import sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class ProvisioningSettings(BaseSettings):
    postgres_admin_dsn: str
    app_database_name: str = "db_health_monitor"
    app_database_user: str = "db_health_app"
    app_database_password: SecretStr

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


def validated_identifier(value: str, variable_name: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            f"{variable_name} debe empezar con letra minúscula y contener solo a-z, 0-9 o _."
        )
    return value


def role_exists(cursor: psycopg.Cursor[tuple[object, ...]], role_name: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
    return cursor.fetchone() is not None


def database_exists(cursor: psycopg.Cursor[tuple[object, ...]], database_name: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
    return cursor.fetchone() is not None


def provision() -> None:
    settings = ProvisioningSettings()
    database_name = validated_identifier(
        settings.app_database_name, "APP_DATABASE_NAME"
    )
    app_user = validated_identifier(
        settings.app_database_user, "APP_DATABASE_USER"
    )
    app_password = settings.app_database_password.get_secret_value()

    with (
        psycopg.connect(settings.postgres_admin_dsn, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        if role_exists(cursor, app_user):
            cursor.execute(
                sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(app_user)),
                (app_password,),
            )
        else:
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(app_user)),
                (app_password,),
            )

        if not database_exists(cursor, database_name):
            cursor.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database_name), sql.Identifier(app_user)
                )
            )
        else:
            cursor.execute(
                sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(app_user)
                )
            )

    print(f"Base '{database_name}' lista para migraciones; rol de aplicación '{app_user}' listo.")


if __name__ == "__main__":
    try:
        provision()
    except (RuntimeError, ValueError, psycopg.Error) as error:
        print(f"No se pudo aprovisionar PostgreSQL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
