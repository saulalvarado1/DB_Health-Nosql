import csv
import io
from datetime import UTC, datetime
from typing import Any

from app.infrastructure.persistence.models import MonitoredDatabase
from app.services.history import MonitoringHistoryEntry


class ReportExportService:
    """Genera reportes de salud estructurados en CSV y JSON a partir del historial de una instancia."""

    def __init__(self, database: MonitoredDatabase, entries: list[MonitoringHistoryEntry]) -> None:
        self._database = database
        self._entries = entries

    def export_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Metadatos de cabecera del reporte
        writer.writerow(["# DB HEALTH MONITOR - REPORTE DE SALUD AUDITABLE"])
        writer.writerow(["# Instancia", self._database.name])
        writer.writerow(["# Motor NoSQL", self._database.engine_id.upper()])
        writer.writerow(["# Intervalo de monitoreo (segundos)", self._database.interval_seconds])
        writer.writerow(["# Total de muestras analizadas", len(self._entries)])
        writer.writerow(
            ["# Fecha de generacion (UTC)", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")]
        )
        writer.writerow([])

        if not self._entries:
            writer.writerow(["Mensaje", "No se registran muestras historicas para esta instancia."])
            return output.getvalue()

        # 2. Obtener la lista unificada de codigos de metricas para las columnas
        metric_codes: list[str] = []
        for entry in self._entries:
            for val in entry.sample.values:
                code = val.metric_definition.code
                if code not in metric_codes:
                    metric_codes.append(code)

        headers = [
            "Fecha_Recoleccion_UTC",
            "Puntuacion_Salud",
            "Estado_Salud",
            "Recoleccion_Exitosa",
            "Error",
        ] + [f"{code} ({self._get_unit(code)})" for code in metric_codes]
        writer.writerow(headers)

        # 3. Filas cronologicas de muestras
        for entry in self._entries:
            sample = entry.sample
            values_by_code = {
                v.metric_definition.code: float(v.numeric_value) for v in sample.values
            }
            row = [
                sample.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
                sample.health_assessment.score if sample.health_assessment else "",
                sample.health_assessment.status.value if sample.health_assessment else "",
                "SI" if sample.collection_succeeded else "NO",
                sample.error_message or "",
            ]
            for code in metric_codes:
                val = values_by_code.get(code)
                row.append(f"{val:.2f}" if val is not None else "")
            writer.writerow(row)

        return output.getvalue()

    def export_json(self) -> dict[str, Any]:
        latest_assessment = (
            self._entries[0].sample.health_assessment
            if self._entries and self._entries[0].sample.health_assessment
            else None
        )
        return {
            "metadata": {
                "generated_at": datetime.now(UTC).isoformat(),
                "service": "DB Health Monitor",
                "version": "1.0",
            },
            "database": {
                "id": str(self._database.id),
                "name": self._database.name,
                "engine": self._database.engine_id,
                "interval_seconds": self._database.interval_seconds,
                "is_enabled": self._database.is_enabled,
                "created_at": self._database.created_at.isoformat(),
            },
            "summary": {
                "total_samples": len(self._entries),
                "latest_health_score": latest_assessment.score if latest_assessment else None,
                "latest_health_status": (
                    latest_assessment.status.value if latest_assessment else None
                ),
            },
            "samples": [
                {
                    "sample_id": str(entry.sample.id),
                    "collected_at": entry.sample.collected_at.isoformat(),
                    "collection_succeeded": entry.sample.collection_succeeded,
                    "error_message": entry.sample.error_message,
                    "health_score": (
                        entry.sample.health_assessment.score
                        if entry.sample.health_assessment
                        else None
                    ),
                    "health_status": (
                        entry.sample.health_assessment.status.value
                        if entry.sample.health_assessment
                        else None
                    ),
                    "metrics": [
                        {
                            "code": val.metric_definition.code,
                            "display_name": val.metric_definition.display_name,
                            "value": float(val.numeric_value),
                            "unit": val.metric_definition.unit,
                            "status": (
                                entry.diagnostics[val.metric_definition.code].status.value
                                if val.metric_definition.code in entry.diagnostics
                                else "ok"
                            ),
                            "message": (
                                entry.diagnostics[val.metric_definition.code].message
                                if val.metric_definition.code in entry.diagnostics
                                else ""
                            ),
                        }
                        for val in entry.sample.values
                    ],
                }
                for entry in self._entries
            ],
        }

    def _get_unit(self, code: str) -> str:
        for entry in self._entries:
            for val in entry.sample.values:
                if val.metric_definition.code == code:
                    return val.metric_definition.unit
        return ""
