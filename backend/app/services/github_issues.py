"""Servicio de integración para crear incidencias automáticas (Issues) en GitHub ante alertas críticas."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
GITHUB_API_BASE = "https://api.github.com"


@dataclass(frozen=True, slots=True)
class GitHubIssueResult:
    created: bool
    issue_number: int | None = None
    issue_url: str | None = None
    error_message: str | None = None


class GitHubIssueService:
    """Abre y gestiona GitHub Issues cuando una base de datos experimenta incidentes críticos."""

    def __init__(
        self,
        token: str | None = None,
        repository: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._token = (
            token
            or (settings.github_token.get_secret_value() if settings.github_token else None)
        )
        self._repository = repository or settings.github_repository
        self._http_client = http_client

    def create_critical_alert_issue(
        self,
        *,
        database_name: str,
        engine_id: str,
        health_score: int,
        error_detail: str,
        labels: list[str] | None = None,
    ) -> GitHubIssueResult:
        """Crea un issue en GitHub con la telemetría del incidente."""
        if not self._token:
            logger.info("GitHub Issues omitido: GITHUB_TOKEN no configurado en entorno.")
            return GitHubIssueResult(
                created=False,
                error_message="GITHUB_TOKEN no configurado en el servidor.",
            )

        url = f"{GITHUB_API_BASE}/repos/{self._repository}/issues"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        title = f"🚨 [CRITICAL ALERT] Falla de salud en base de datos: {database_name} ({engine_id.upper()})"
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        body = (
            "## 🚨 Incidente de Salud Crítico Detectado por DB Health Monitor\n\n"
            "Se ha detectado una degradación crítica o pérdida total de conectividad en una base de datos monitoreada.\n\n"
            "### 📋 Detalles de la Instancia\n"
            f"- **Nombre:** `{database_name}`\n"
            f"- **Motor de Base de Datos:** `{engine_id.upper()}`\n"
            f"- **Puntaje de Salud (Health Score):** 🔴 **{health_score} / 100**\n"
            f"- **Fecha y Hora de Detección:** `{now_str}`\n\n"
            "### 💥 Causa de la Alerta\n"
            "```text\n"
            f"{error_detail}\n"
            "```\n\n"
            "### 🛠️ Acciones Recomendadas para el DBA\n"
            "1. Verificar conectividad de red y disponibilidad del puerto (`27017` para MongoDB, `6379` para Redis).\n"
            "2. Revisar consumo de recursos y memoria en el host de la base de datos.\n"
            "3. Consultar el historial completo de telemetría en el [Dashboard de DB Health Monitor](https://frontend-production-07c5.up.railway.app).\n\n"
            "---\n"
            "*Ticket generado automáticamente por el subsistema de telemetría de **DB Health Monitor (v1.0)** — Grupo 3 (UPT).*\n"
        )

        payload: dict[str, Any] = {
            "title": title,
            "body": body,
            "labels": labels or ["bug", "critical-alert", "automated-monitoring"],
        }

        try:
            if self._http_client is not None:
                resp = self._http_client.post(url, headers=headers, json=payload, timeout=10.0)
            else:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, json=payload)

            if resp.status_code in {200, 201}:
                data = resp.json()
                issue_number = data.get("number")
                html_url = data.get("html_url")
                logger.info("GitHub Issue #%s creado exitosamente: %s", issue_number, html_url)
                return GitHubIssueResult(created=True, issue_number=issue_number, issue_url=html_url)

            logger.warning("GitHub API retornó código %s al crear issue: %s", resp.status_code, resp.text)
            return GitHubIssueResult(
                created=False,
                error_message=f"GitHub API respondió con código {resp.status_code}: {resp.text}",
            )
        except Exception as err:  # noqa: BLE001
            logger.warning("Fallo al conectar con la API de GitHub: %s", err)
            return GitHubIssueResult(created=False, error_message=f"Error de red con GitHub: {err}")
