"""Tests for GitHub integration."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from jerry.integrations.github.client import GitHubClient

@pytest.mark.asyncio
async def test_get_installation_client(settings, mock_github):
    """Test getting an installation client."""
    with patch('github.GithubIntegration') as mock_integration:
        mock_integration.return_value.get_access_token.return_value = Mock(token="test-token")
        
        client = GitHubClient(settings)
        gh_client = await client.get_installation_client(123)
        
        mock_integration.assert_called_once()
        assert gh_client is not None

@pytest.mark.asyncio
async def test_get_pr_files(settings, mock_github):
    """Test getting PR files."""
    with patch('github.GithubIntegration'):
        client = GitHubClient(settings)
        with patch.object(client, 'get_installation_client', return_value=mock_github):
            files = await client.get_pr_files(123, "test/repo", 1)
            
            assert len(files) == 1
            assert files[0]['filename'] == "test.py"
            assert files[0]['status'] == "modified"
            assert files[0]['additions'] == 10
            assert files[0]['deletions'] == 5

@pytest.mark.asyncio
async def test_get_repo_context(settings, mock_github):
    """Test getting repository context."""
    with patch('github.GithubIntegration'):
        client = GitHubClient(settings)
        with patch.object(client, 'get_installation_client', return_value=mock_github):
            pr_files = [{'filename': 'test.py'}]
            context = await client.get_repo_context(123, "test/repo", pr_files)
            
            assert "Repository:" in context
            mock_github.get_repo.assert_called_once_with("test/repo")

@pytest.mark.asyncio
async def test_comment_on_pr(settings, mock_github):
    """Test commenting on a PR."""
    with patch('github.GithubIntegration'):
        client = GitHubClient(settings)
        with patch.object(client, 'get_installation_client', return_value=mock_github):
            await client.comment_on_pr(123, "test/repo", 1, "Test comment")
            
            mock_github.get_repo.assert_called_once()
            mock_github.get_repo().get_pull.assert_called_once_with(1)
            mock_github.get_repo().get_pull().create_issue_comment.assert_called_once_with("Test comment")

@pytest.mark.asyncio
async def test_handle_pr_event(settings, mock_github):
    """Test handling PR events."""
    mock_ai = AsyncMock()
    mock_ai.review_pr.return_value = "AI review comment"
    
    event = {
        'action': 'opened',
        'installation': {'id': 123},
        'repository': {'full_name': 'test/repo'},
        'pull_request': {
            'number': 1,
            'html_url': 'https://github.com/test/repo/pull/1',
            'body': 'Test PR'
        }
    }
    
    with patch('github.GithubIntegration'):
        client = GitHubClient(settings)
        with patch.object(client, 'get_installation_client', return_value=mock_github):
            with patch('jerry.api.app.app') as mock_app:
                mock_app.state.ai = mock_ai
                await client.handle_pr_event(event)
                
                mock_ai.review_pr.assert_called_once()
                assert mock_github.get_repo().get_pull().create_issue_comment.called

@pytest.mark.asyncio
async def test_handle_pr_comment(settings, mock_github):
    """Test handling PR comments."""
    mock_ai = AsyncMock()
    mock_ai.review_pr.return_value = "AI review comment"
    
    event = {
        'comment': {'body': '/jerry review'},
        'installation': {'id': 123},
        'repository': {'full_name': 'test/repo'},
        'issue': {'number': 1}
    }
    
    with patch('github.GithubIntegration'):
        client = GitHubClient(settings)
        with patch.object(client, 'get_installation_client', return_value=mock_github):
            with patch('jerry.api.app.app') as mock_app:
                mock_app.state.ai = mock_ai
                await client.handle_pr_comment(event)
                
                mock_ai.review_pr.assert_called_once()
                assert mock_github.get_repo().get_pull().create_issue_comment.called

@pytest.mark.asyncio
async def test_ignore_non_review_comment(settings, mock_github):
    """Test ignoring non-review comments."""
    event = {
        'comment': {'body': 'regular comment'},
        'installation': {'id': 123},
        'repository': {'full_name': 'test/repo'},
        'issue': {'number': 1}
    }
    
    with patch('github.GithubIntegration'):
        client = GitHubClient(settings)
        with patch.object(client, 'get_installation_client', return_value=mock_github):
            await client.handle_pr_comment(event)
            
            assert not mock_github.get_repo().get_pull().create_issue_comment.called 