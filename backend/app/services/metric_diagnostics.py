from dataclasses import dataclass

from app.domain.models import MetricDiagnosticBasis, MetricDiagnosticStatus
from app.services.health_score import HealthRule, severity_for_rule


@dataclass(frozen=True, slots=True)
class MetricDiagnostic:
    status: MetricDiagnosticStatus
    basis: MetricDiagnosticBasis
    message: str


def _diagnostic(
    status: MetricDiagnosticStatus,
    basis: MetricDiagnosticBasis,
    message: str,
) -> MetricDiagnostic:
    return MetricDiagnostic(status=status, basis=basis, message=message)


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _impact(metric_code: str) -> str:
    impacts = {
        "availability": (
            "Si deja de responder, el monitor no podrá recolectar datos hasta que se "
            "recupere la conexión."
        ),
        "memory_usage_percent": (
            "Redis puede expulsar claves o rechazar escrituras, según su política de memoria."
        ),
        "connections_usage_percent": (
            "Las conexiones nuevas pueden demorarse o ser rechazadas si se agota la capacidad."
        ),
        "wiredtiger_cache_usage_percent": (
            "Una presión sostenida de caché puede aumentar la latencia de lectura y escritura."
        ),
    }
    return impacts.get(metric_code, "El comportamiento puede degradarse si la condición persiste.")


def _diagnose_with_threshold(
    *, metric_code: str, value: float, rule: HealthRule
) -> MetricDiagnostic:
    severity = severity_for_rule(value, rule)
    impact = _impact(metric_code)
    if severity is None:
        comparator = "por debajo" if rule.direction == "above" else "por encima"
        return _diagnostic(
            MetricDiagnosticStatus.HEALTHY,
            MetricDiagnosticBasis.THRESHOLD,
            f"Está {comparator} del umbral de advertencia configurado "
            f"({_number(rule.warning_value)}).",
        )
    if severity.value == "warning":
        return _diagnostic(
            MetricDiagnosticStatus.WARNING,
            MetricDiagnosticBasis.THRESHOLD,
            f"Alcanzó el umbral de advertencia configurado "
            f"({_number(rule.warning_value)}). {impact}",
        )
    return _diagnostic(
        MetricDiagnosticStatus.CRITICAL,
        MetricDiagnosticBasis.THRESHOLD,
        f"Alcanzó el umbral crítico configurado ({_number(rule.critical_value)}). {impact}",
    )


def _diagnose_cumulative_incident(
    *,
    value: float,
    previous_value: float | None,
    event_name: str,
    impact: str,
) -> MetricDiagnostic:
    if previous_value is None:
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                f"No se han registrado {event_name} desde el inicio del servicio.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.INFORMATIONAL,
            MetricDiagnosticBasis.INFORMATIONAL,
            f"El servicio acumula {_number(value)} {event_name}, pero no hay una muestra "
            "anterior para saber cuándo ocurrieron.",
        )

    if value > previous_value:
        return _diagnostic(
            MetricDiagnosticStatus.WARNING,
            MetricDiagnosticBasis.HEURISTIC,
            f"Se detectaron {_number(value - previous_value)} {event_name} desde la muestra "
            f"anterior. {impact}",
        )
    if value == previous_value:
        return _diagnostic(
            MetricDiagnosticStatus.HEALTHY,
            MetricDiagnosticBasis.HEURISTIC,
            f"No hubo nuevos {event_name} desde la muestra anterior.",
        )
    return _diagnostic(
        MetricDiagnosticStatus.INFORMATIONAL,
        MetricDiagnosticBasis.INFORMATIONAL,
        "El contador se reinició, normalmente porque el servicio volvió a iniciarse.",
    )


def diagnose_metric(
    *,
    metric_code: str,
    value: float,
    rule: HealthRule | None,
    previous_value: float | None,
) -> MetricDiagnostic:
    """Explica una métrica sin convertir heurísticas en alertas del sistema."""
    if rule is not None:
        return _diagnose_with_threshold(metric_code=metric_code, value=value, rule=rule)

    if metric_code == "availability":
        if value > 0:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "La instancia respondió correctamente a la comprobación de lectura.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.CRITICAL,
            MetricDiagnosticBasis.HEURISTIC,
            "La instancia no respondió; no será posible recolectar sus métricas.",
        )

    if metric_code in {"connections_usage_percent", "memory_usage_percent"}:
        if value >= 90:
            return _diagnostic(
                MetricDiagnosticStatus.CRITICAL,
                MetricDiagnosticBasis.HEURISTIC,
                "Utiliza al menos el 90% de la capacidad disponible; puede quedarse sin margen.",
            )
        if value >= 80:
            return _diagnostic(
                MetricDiagnosticStatus.WARNING,
                MetricDiagnosticBasis.HEURISTIC,
                "Supera el 80% de la capacidad disponible; conviene vigilar su crecimiento.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.HEALTHY,
            MetricDiagnosticBasis.HEURISTIC,
            "Permanece por debajo del 80% de la capacidad disponible.",
        )

    if metric_code == "wiredtiger_cache_usage_percent":
        if value >= 95:
            return _diagnostic(
                MetricDiagnosticStatus.CRITICAL,
                MetricDiagnosticBasis.HEURISTIC,
                "La caché está cerca de su capacidad; la presión de expulsión puede elevar la latencia.",
            )
        if value >= 80:
            return _diagnostic(
                MetricDiagnosticStatus.WARNING,
                MetricDiagnosticBasis.HEURISTIC,
                "La caché superó la referencia orientativa del 80%; revisa si la presión se mantiene.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.HEALTHY,
            MetricDiagnosticBasis.HEURISTIC,
            "La caché se mantiene por debajo de la referencia orientativa del 80%.",
        )

    if metric_code == "wiredtiger_cache_dirty_percent":
        if value >= 20:
            return _diagnostic(
                MetricDiagnosticStatus.CRITICAL,
                MetricDiagnosticBasis.HEURISTIC,
                "Los datos modificados ocupan al menos el 20% de la caché; la presión de "
                "checkpoint y expulsión puede elevar la latencia.",
            )
        if value >= 5:
            return _diagnostic(
                MetricDiagnosticStatus.WARNING,
                MetricDiagnosticBasis.HEURISTIC,
                "Los datos modificados ocupan al menos el 5% de la caché; conviene vigilar "
                "si la presión continúa aumentando.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.HEALTHY,
            MetricDiagnosticBasis.HEURISTIC,
            "Los datos modificados permanecen por debajo de la referencia orientativa del 5%.",
        )

    if metric_code == "global_lock_queue_total":
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "No hay operaciones esperando adquirir un bloqueo.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.WARNING,
            MetricDiagnosticBasis.HEURISTIC,
            "Hay operaciones esperando un bloqueo; si la cola persiste puede aumentar la latencia.",
        )

    if metric_code == "connections_available":
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.CRITICAL,
                MetricDiagnosticBasis.HEURISTIC,
                "MongoDB no informa conexiones disponibles; los clientes nuevos podrían ser rechazados.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.INFORMATIONAL,
            MetricDiagnosticBasis.INFORMATIONAL,
            "Es la capacidad restante informada por MongoDB; debe evaluarse junto con su tendencia.",
        )

    if metric_code == "blocked_clients":
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "No hay clientes esperando operaciones bloqueantes.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.WARNING,
            MetricDiagnosticBasis.HEURISTIC,
            "Hay clientes bloqueados. Puede ser intencional con comandos bloqueantes; si no lo es, "
            "puede aumentar la espera de la aplicación.",
        )

    if metric_code == "evicted_keys":
        return _diagnose_cumulative_incident(
            value=value,
            previous_value=previous_value,
            event_name="claves expulsadas",
            impact="Redis está liberando datos por presión de memoria.",
        )

    if metric_code == "rejected_connections":
        return _diagnose_cumulative_incident(
            value=value,
            previous_value=previous_value,
            event_name="conexiones rechazadas",
            impact="Algunos clientes no pudieron conectarse; revisa maxclients y conexiones abiertas.",
        )

    if metric_code == "persistence_last_save_success":
        if value > 0:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "El último guardado RDB en segundo plano terminó correctamente.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.CRITICAL,
            MetricDiagnosticBasis.HEURISTIC,
            "El último guardado RDB falló; la copia persistente puede estar desactualizada.",
        )

    if metric_code == "loading":
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "Redis terminó de cargar sus datos y está operativo.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.WARNING,
            MetricDiagnosticBasis.HEURISTIC,
            "Redis está cargando datos; algunas solicitudes pueden no estar disponibles todavía.",
        )

    if metric_code == "keyspace_hit_rate_percent":
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.INFORMATIONAL,
                MetricDiagnosticBasis.INFORMATIONAL,
                "No hay aciertos registrados; también puede significar que todavía no hubo búsquedas.",
            )
        if value >= 80:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "Al menos el 80% de las búsquedas encontró la clave solicitada.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.WARNING,
            MetricDiagnosticBasis.HEURISTIC,
            "Menos del 80% de las búsquedas encontró la clave; revisa expiraciones y patrón de caché.",
        )

    if metric_code == "memory_fragmentation_ratio":
        if value == 0:
            return _diagnostic(
                MetricDiagnosticStatus.INFORMATIONAL,
                MetricDiagnosticBasis.INFORMATIONAL,
                "Redis no informó una razón de fragmentación utilizable.",
            )
        if value < 1:
            return _diagnostic(
                MetricDiagnosticStatus.WARNING,
                MetricDiagnosticBasis.HEURISTIC,
                "La razón es menor que 1; parte de la memoria puede estar paginada y causar latencia.",
            )
        if value <= 1.5:
            return _diagnostic(
                MetricDiagnosticStatus.HEALTHY,
                MetricDiagnosticBasis.HEURISTIC,
                "La relación entre memoria residente y asignada está en el rango orientativo 1–1.5.",
            )
        if value <= 2:
            return _diagnostic(
                MetricDiagnosticStatus.WARNING,
                MetricDiagnosticBasis.HEURISTIC,
                "La fragmentación supera 1.5; Redis consume más memoria residente de la asignada.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.CRITICAL,
            MetricDiagnosticBasis.HEURISTIC,
            "La fragmentación supera 2; el sobreconsumo de memoria del proceso es elevado.",
        )

    if metric_code == "uptime_seconds":
        if previous_value is None:
            return _diagnostic(
                MetricDiagnosticStatus.INFORMATIONAL,
                MetricDiagnosticBasis.INFORMATIONAL,
                "Es la primera referencia disponible; todavía no se puede detectar un reinicio.",
            )
        if value < previous_value:
            return _diagnostic(
                MetricDiagnosticStatus.WARNING,
                MetricDiagnosticBasis.HEURISTIC,
                "El tiempo activo disminuyó; el servicio se reinició entre las dos últimas muestras.",
            )
        return _diagnostic(
            MetricDiagnosticStatus.HEALTHY,
            MetricDiagnosticBasis.HEURISTIC,
            "El tiempo activo aumentó con normalidad; no se detectó un reinicio.",
        )

    informational_messages = {
        "connections_current": (
            "Es una cantidad instantánea. Sin conocer el límite no indica una falla por sí sola; "
            "compárala con el porcentaje de uso de conexiones."
        ),
        "memory_resident_mb": (
            "Es informativa porque el valor saludable depende de la memoria disponible en el host."
        ),
        "connections_active": (
            "Muestra conexiones ejecutando trabajo ahora; necesita una línea base de carga para "
            "calificarla."
        ),
        "global_lock_active_clients": (
            "Es una cantidad instantánea de clientes activos y depende de la carga esperada."
        ),
        "open_cursors": (
            "Los cursores abiertos son normales; una tendencia creciente puede revelar cursores "
            "que la aplicación no cierra."
        ),
        "documents_read_total": (
            "Es un contador acumulado de documentos devueltos; su crecimiento representa actividad."
        ),
        "documents_written_total": (
            "Es un contador acumulado de escrituras; necesita compararse con el tiempo y la carga."
        ),
        "query_scanned_keys_total": (
            "Es un contador acumulado; compáralo con resultados y documentos examinados para "
            "evaluar la eficiencia de índices."
        ),
        "query_scanned_documents_total": (
            "Es un contador acumulado; un crecimiento desproporcionado puede indicar consultas "
            "sin índices adecuados."
        ),
        "network_requests_total": (
            "Es un contador acumulado de solicitudes de red y confirma actividad del servicio."
        ),
        "network_bytes_in": (
            "Es un contador acumulado de tráfico recibido; que aumente es normal mientras haya actividad."
        ),
        "network_bytes_out": (
            "Es un contador acumulado de tráfico enviado; que aumente es normal mientras haya actividad."
        ),
        "operations_total": (
            "Es un contador acumulado; un valor alto confirma actividad, no una falla por sí solo."
        ),
        "connected_clients": (
            "Es una cantidad instantánea y necesita compararse con la capacidad configurada."
        ),
        "operations_per_second": (
            "Mide actividad instantánea; un valor alto o bajo depende de la carga esperada."
        ),
        "total_connections_received": (
            "Es un contador acumulado de conexiones aceptadas; úsalo para observar rotación de clientes."
        ),
        "total_commands_processed": (
            "Es un contador acumulado de comandos y representa actividad, no una falla por sí solo."
        ),
        "expired_keys": (
            "Es un contador acumulado de expiraciones esperadas según los TTL configurados."
        ),
        "keyspace_hits_total": (
            "Es un contador acumulado; el porcentaje de aciertos permite interpretarlo mejor."
        ),
        "keyspace_misses_total": (
            "Es un contador acumulado; el porcentaje de aciertos permite interpretarlo mejor."
        ),
        "network_input_bytes_total": (
            "Es tráfico recibido acumulado; que aumente es normal mientras exista actividad."
        ),
        "network_output_bytes_total": (
            "Es tráfico enviado acumulado; que aumente es normal mientras exista actividad."
        ),
        "instantaneous_input_kbps": (
            "Mide tráfico entrante instantáneo y debe compararse con la capacidad de la red."
        ),
        "instantaneous_output_kbps": (
            "Mide tráfico saliente instantáneo y debe compararse con la capacidad de la red."
        ),
        "pubsub_channels": (
            "Indica canales con suscriptores; cero también es correcto si no se usa Pub/Sub."
        ),
        "keys_total": (
            "Es el tamaño lógico actual del conjunto de datos y necesita una línea base propia."
        ),
        "expiring_keys_total": (
            "Indica cuántas claves tienen TTL; su valor correcto depende del diseño de la aplicación."
        ),
        "connected_replicas": (
            "Cero es normal en un nodo independiente; en producción debe compararse con las "
            "réplicas esperadas."
        ),
        "latest_fork_microseconds": (
            "La duración aceptable depende del tamaño de datos, el host y la política de persistencia."
        ),
        "used_memory_bytes": (
            "Es la memoria absoluta usada; el porcentaje de memoria determina mejor el margen disponible."
        ),
    }
    return _diagnostic(
        MetricDiagnosticStatus.INFORMATIONAL,
        MetricDiagnosticBasis.INFORMATIONAL,
        informational_messages.get(
            metric_code,
            "No existe un criterio universal para esta métrica; necesita una línea base del entorno.",
        ),
    )
