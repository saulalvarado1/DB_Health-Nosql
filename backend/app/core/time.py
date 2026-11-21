from datetime import UTC, datetime, timedelta, timezone

# Zona horaria oficial de Perú (America/Lima / UTC-5).
# En Perú no se aplica horario de verano, por lo que UTC-5 es constante todo el año.
PERU_TZ = timezone(timedelta(hours=-5), name="PET")


def to_peru_time(dt: datetime | None = None) -> datetime:
    """Convierte un datetime a la zona horaria de Perú (UTC-5).

    Si dt es None, toma el momento actual en UTC y lo convierte.
    Si dt no tiene timezone (naive), asume que está en UTC antes de convertir.
    """
    if dt is None:
        dt = datetime.now(UTC)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(PERU_TZ)


def format_peru_time(dt: datetime | None = None, *, include_tz_label: bool = True) -> str:
    """Formatea la fecha y hora para visualización de usuario en Perú.

    Ejemplo de salida con include_tz_label=True:
        '2026-11-20 17:44:56 (Hora Perú, UTC-5)'
    Ejemplo de salida con include_tz_label=False:
        '2026-11-20 17:44:56'
    """
    pdt = to_peru_time(dt)
    formatted = pdt.strftime("%Y-%m-%d %H:%M:%S")
    if include_tz_label:
        return f"{formatted} (Hora Perú, UTC-5)"
    return formatted
