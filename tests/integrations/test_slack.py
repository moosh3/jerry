"""Tests for Slack integration."""

import pytest
from unittest.mock import patch, AsyncMock, Mock
from slack_bolt import App
from jerry.integrations.slack.client import SlackClient, CommandError

@pytest.fixture
def mock_bolt_app():
    """Create a mock Bolt app."""
    mock = Mock(spec=App)
    mock.client = AsyncMock()
    mock.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    return mock

@pytest.mark.asyncio
async def test_handle_help_message(settings, mock_bolt_app):
    """Test handling help message."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Simulate help message
        message = {"text": "help", "channel": "test-channel"}
        say = AsyncMock()
        
        await client.app.message("help")(message, say, Mock())
        
        assert say.called
        args = say.call_args[0][0]
        assert "Here's what I can help you with" in args

@pytest.mark.asyncio
async def test_handle_create_ticket(settings, mock_bolt_app):
    """Test handling ticket creation command."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Simulate create ticket command
        command = {"text": "create ticket", "channel_id": "test-channel"}
        ack = AsyncMock()
        say = AsyncMock()
        
        await client._handle_create_ticket(say, command, {})
        
        assert ack.called
        assert say.called
        blocks = say.call_args[0][0]["blocks"]
        assert any(block["block_id"] == "ticket_title" for block in blocks)

@pytest.mark.asyncio
async def test_handle_close_ticket(settings, mock_bolt_app):
    """Test handling ticket closing command."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Simulate close ticket command
        command = {"text": "close ticket TEST-123", "channel_id": "test-channel"}
        say = AsyncMock()
        
        await client._handle_close_ticket(say, command, {})
        
        assert say.called
        blocks = say.call_args[0][0]["blocks"]
        assert any(block["block_id"] == "close_reason" for block in blocks)

@pytest.mark.asyncio
async def test_handle_update_ticket(settings, mock_bolt_app):
    """Test handling ticket update command."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Simulate update ticket command
        command = {
            "text": "update ticket TEST-123 This is an update",
            "channel_id": "test-channel"
        }
        say = AsyncMock()
        
        with patch('jerry.api.app.app') as mock_app:
            mock_app.state.jira = AsyncMock()
            await client._handle_update_ticket(say, command, {})
            
            assert say.called
            assert "Added comment to ticket" in say.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_review_pr(settings, mock_bolt_app):
    """Test handling PR review command."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Simulate review PR command
        command = {"text": "review", "channel_id": "test-channel"}
        say = AsyncMock()
        
        await client._handle_review_pr(say, command, {})
        
        assert say.called
        blocks = say.call_args[0][0]["blocks"]
        assert any(block["block_id"] == "pr_url" for block in blocks)

@pytest.mark.asyncio
async def test_handle_invalid_command(settings, mock_bolt_app):
    """Test handling invalid command."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Simulate invalid command
        command = {"text": "invalid command", "channel_id": "test-channel"}
        say = AsyncMock()
        
        await client._handle_unknown_command(say, command, {})
        
        assert say.called
        assert "don't understand that command" in say.call_args[0][0]

@pytest.mark.asyncio
async def test_error_handling(settings, mock_bolt_app):
    """Test error handling in commands."""
    with patch('slack_bolt.App', return_value=mock_bolt_app):
        client = SlackClient(settings)
        
        # Test global error handler
        error = CommandError("Test error")
        body = {"channel": {"id": "test-channel"}}
        
        await client.app.error(error, body, Mock())
        
        assert mock_bolt_app.client.chat_postMessage.called
        message = mock_bolt_app.client.chat_postMessage.call_args[1]["text"]
        assert "❌" in message 