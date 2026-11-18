from unittest.mock import MagicMock

from app.services.github_issues import GitHubIssueService


def test_github_issue_service_without_token() -> None:
    service = GitHubIssueService(token="")
    result = service.create_critical_alert_issue(
        database_name="mongodb-prod",
        engine_id="mongodb",
        health_score=0,
        error_detail="Timeout de conexión",
    )
    assert not result.created
    assert "no configurado" in (result.error_message or "")


def test_github_issue_service_success() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "number": 42,
        "html_url": "https://github.com/UPT-FAING-EPIS/repo/issues/42",
    }
    mock_client.post.return_value = mock_response

    service = GitHubIssueService(token="ghp_testtoken123", repository="UPT-FAING-EPIS/repo", http_client=mock_client)
    result = service.create_critical_alert_issue(
        database_name="redis-cache",
        engine_id="redis",
        health_score=0,
        error_detail="Memoria al 99%",
    )
    assert result.created
    assert result.issue_number == 42
    assert "issues/42" in (result.issue_url or "")
    mock_client.post.assert_called_once()


def test_github_issue_service_without_repository() -> None:
    service = GitHubIssueService(token="ghp_token", repository="")
    result = service.create_critical_alert_issue(
        database_name="mongodb-prod",
        engine_id="mongodb",
        health_score=0,
        error_detail="Timeout de red",
    )
    assert not result.created
    assert "Repositorio de GitHub no configurado" in (result.error_message or "")


def test_monitored_database_response_masks_github_token() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4
    from app.api.presenters import monitored_database_response
    from app.core.secrets import CredentialsCipher
    from app.infrastructure.persistence.models import MonitoredDatabase, MonitoringSchedule

    cipher = CredentialsCipher()
    database = MonitoredDatabase(
        id=uuid4(),
        owner_id=uuid4(),
        engine_id="mongodb",
        name="Test Database",
        connection_uri_encrypted="dummy",
        is_enabled=True,
        github_issues_enabled=True,
        github_repository="usuario/mi-repo",
        github_token_encrypted=cipher.encrypt("ghp_secret_access_token"),
    )
    database.schedule = MonitoringSchedule(interval_seconds=30)
    database.created_at = datetime.now(UTC)

    response = monitored_database_response(database)

    assert response.github_issues_enabled is True
    assert response.github_repository == "usuario/mi-repo"
    assert response.has_github_token is True
    assert not hasattr(response, "github_token")
    assert not hasattr(response, "github_token_encrypted")


def test_update_request_validation_accepts_github_changes() -> None:
    from app.api.schemas.monitored_databases import UpdateMonitoredDatabaseRequest

    req = UpdateMonitoredDatabaseRequest(
        github_issues_enabled=True,
        github_repository="owner/repo-incidents",
    )
    assert req.github_issues_enabled is True
    assert req.github_repository == "owner/repo-incidents"


def test_dispatch_github_issue_skips_when_disabled() -> None:
    from unittest.mock import patch
    from uuid import uuid4
    from app.infrastructure.persistence.models import MonitoredDatabase
    from app.services.monitoring import MonitoringService

    database = MonitoredDatabase(
        id=uuid4(),
        owner_id=uuid4(),
        engine_id="mongodb",
        name="Test Database",
        connection_uri_encrypted="dummy",
        is_enabled=True,
        github_issues_enabled=False,
    )

    with patch("app.services.github_issues.GitHubIssueService.create_critical_alert_issue") as mock_create:
        MonitoringService._dispatch_github_issue(database, "Error grave", 0)
        mock_create.assert_not_called()
