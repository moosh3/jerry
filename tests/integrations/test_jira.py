"""Tests for JIRA integration."""

import pytest
from unittest.mock import patch, Mock
from jerry.integrations.jira.client import JiraClient

@pytest.mark.asyncio
async def test_get_issue(settings, mock_jira):
    """Test getting a JIRA issue."""
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        issue = await client.get_issue("TEST-123")
        
        assert issue.key == "TEST-123"
        assert issue.fields.summary == "Test Issue"
        mock_jira.issue.assert_called_once_with("TEST-123")

@pytest.mark.asyncio
async def test_create_ticket(settings, mock_jira):
    """Test creating a JIRA ticket."""
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        ticket = await client.create_ticket(
            title="[TEST] New Feature",
            description="Test description"
        )
        
        assert ticket.key == "TEST-124"
        mock_jira.create_issue.assert_called_once_with(
            fields={
                'project': {'key': 'TEST'},
                'summary': '[TEST] New Feature',
                'description': 'Test description',
                'issuetype': {'name': 'Task'}
            }
        )

@pytest.mark.asyncio
async def test_close_ticket(settings, mock_jira):
    """Test closing a JIRA ticket."""
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        await client.close_ticket("TEST-123", "Work completed")
        
        mock_jira.add_comment.assert_called_once()
        mock_jira.transition_issue.assert_called_once()

@pytest.mark.asyncio
async def test_link_pr_to_ticket(settings, mock_jira):
    """Test linking a PR to a JIRA ticket."""
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        pr_url = "https://github.com/test/repo/pull/1"
        
        await client.link_pr_to_ticket("TEST-123", pr_url, "opened")
        mock_jira.add_comment.assert_called_once()
        comment = mock_jira.add_comment.call_args[0][1]
        assert "Pull Request opened" in comment
        assert pr_url in comment

@pytest.mark.asyncio
async def test_extract_ticket_ids(settings, mock_jira):
    """Test extracting ticket IDs from text."""
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        text = "Fixed issue TEST-123 and related to TEST-456"
        
        ticket_ids = await client.extract_ticket_ids_from_text(text)
        assert len(ticket_ids) == 2
        assert "TEST-123" in ticket_ids
        assert "TEST-456" in ticket_ids

@pytest.mark.asyncio
async def test_handle_pr_event(settings, mock_jira):
    """Test handling PR events."""
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        pr_url = "https://github.com/test/repo/pull/1"
        description = "Fixes TEST-123: Implement new feature"
        
        await client.handle_pr_event(pr_url, "opened", description)
        
        # Should add comment and update status
        assert mock_jira.add_comment.called
        assert mock_jira.transitions.called

@pytest.mark.asyncio
async def test_get_linked_prs(settings, mock_jira):
    """Test getting PRs linked to a ticket."""
    mock_comments = [
        Mock(body="PR: https://github.com/test/repo/pull/1"),
        Mock(body="Another PR: https://github.com/test/repo/pull/2")
    ]
    mock_jira.comments.return_value = mock_comments
    
    with patch('jira.JIRA', return_value=mock_jira):
        client = JiraClient(settings)
        prs = await client.get_linked_prs("TEST-123")
        
        assert len(prs) == 2
        assert "https://github.com/test/repo/pull/1" in prs
        assert "https://github.com/test/repo/pull/2" in prs 