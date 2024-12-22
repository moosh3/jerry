"""Test configuration and fixtures."""

import pytest
from unittest.mock import Mock, AsyncMock
from jerry.core.config import Settings

@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        # JIRA settings
        jira_api_token="test-token",
        jira_api_user="test-user",
        jira_api_endpoint="https://jira.test.com",
        
        # GitHub settings
        github_app_id="test-app-id",
        github_private_key="test-private-key",
        github_enterprise_url="https://github.test.com",
        github_webhook_secret="test-webhook-secret",
        
        # Slack settings
        slack_bot_token="xoxb-test-token",
        slack_signing_secret="test-signing-secret",
        
        # Azure AI settings
        azure_api_key="test-api-key",
        azure_endpoint="https://azure.test.com"
    )

@pytest.fixture
def mock_jira():
    """Create mock JIRA client."""
    mock = Mock()
    # Mock common JIRA methods
    mock.issue.return_value = Mock(
        key="TEST-123",
        fields=Mock(
            summary="Test Issue",
            description="Test Description",
            status=Mock(name="Open")
        )
    )
    mock.create_issue.return_value = Mock(key="TEST-124")
    mock.add_comment.return_value = None
    mock.transitions.return_value = [
        {"id": "1", "name": "In Progress"},
        {"id": "2", "name": "Done"}
    ]
    return mock

@pytest.fixture
def mock_github():
    """Create mock GitHub client."""
    mock = Mock()
    # Mock repository and pull request
    mock_repo = Mock()
    mock_repo.get_pull.return_value = Mock(
        number=1,
        title="Test PR",
        body="Test Description",
        html_url="https://github.com/test/repo/pull/1",
        get_files=Mock(return_value=[
            Mock(
                filename="test.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                patch="@@ test patch",
                raw_url="https://github.com/test/repo/raw/test.py"
            )
        ])
    )
    mock_repo.get_contents.return_value = Mock(
        decoded_content=b"test content"
    )
    mock.get_repo.return_value = mock_repo
    return mock

@pytest.fixture
def mock_slack():
    """Create mock Slack client."""
    mock = AsyncMock()
    # Mock Slack app and client
    mock.client = AsyncMock()
    mock.client.chat_postMessage = AsyncMock()
    mock.client.chat_postMessage.return_value = {"ok": True, "ts": "123.456"}
    return mock

@pytest.fixture
def mock_azure_openai():
    """Create mock Azure OpenAI client."""
    mock = AsyncMock()
    # Mock chat completion
    mock.chat.completions.create = AsyncMock()
    mock.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="AI generated response"
                )
            )
        ]
    )
    return mock

@pytest.fixture
def mock_text_analytics():
    """Create mock Azure Text Analytics client."""
    mock = Mock()
    # Mock sentiment analysis
    mock.analyze_sentiment.return_value = [
        Mock(sentiment="positive")
    ]
    return mock 