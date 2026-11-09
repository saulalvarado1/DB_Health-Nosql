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
