"""Tests for Azure AI integration."""

import pytest
from unittest.mock import patch, AsyncMock, Mock
from jerry.integrations.azureai.client import AzureAIClient

@pytest.mark.asyncio
async def test_analyze_code(settings, mock_azure_openai):
    """Test code analysis."""
    with patch('openai.AzureOpenAI', return_value=mock_azure_openai):
        client = AzureAIClient(settings)
        
        code = "def test(): pass"
        prompt = "Review this code"
        
        result = await client.analyze_code(code, prompt)
        
        assert result == "AI generated response"
        assert mock_azure_openai.chat.completions.create.called
        call_args = mock_azure_openai.chat.completions.create.call_args[1]
        assert call_args['messages'][1]['content'] == code

@pytest.mark.asyncio
async def test_refine_ticket(settings, mock_azure_openai):
    """Test ticket refinement."""
    with patch('openai.AzureOpenAI', return_value=mock_azure_openai):
        client = AzureAIClient(settings)
        
        description = "Implement new feature"
        context = "Technical details here"
        
        result = await client.refine_ticket(description, context)
        
        assert result == "AI generated response"
        assert mock_azure_openai.chat.completions.create.called
        call_args = mock_azure_openai.chat.completions.create.call_args[1]
        assert "Description:" in call_args['messages'][1]['content']

@pytest.mark.asyncio
async def test_review_pr(settings, mock_azure_openai):
    """Test PR review."""
    with patch('openai.AzureOpenAI', return_value=mock_azure_openai):
        client = AzureAIClient(settings)
        
        pr_diff = "diff content"
        repo_context = "repo info"
        
        result = await client.review_pr(pr_diff, repo_context)
        
        assert result == "AI generated response"
        assert mock_azure_openai.chat.completions.create.called
        call_args = mock_azure_openai.chat.completions.create.call_args[1]
        assert pr_diff in call_args['messages'][1]['content']

@pytest.mark.asyncio
async def test_generate_slack_response(settings, mock_azure_openai):
    """Test Slack response generation."""
    with patch('openai.AzureOpenAI', return_value=mock_azure_openai):
        client = AzureAIClient(settings)
        
        message = "help me"
        context = "user needs assistance"
        
        result = await client.generate_slack_response(message, context)
        
        assert result == "AI generated response"
        assert mock_azure_openai.chat.completions.create.called
        call_args = mock_azure_openai.chat.completions.create.call_args[1]
        assert message in call_args['messages'][1]['content']

@pytest.mark.asyncio
async def test_analyze_sentiment(settings, mock_text_analytics):
    """Test sentiment analysis."""
    with patch('azure.ai.textanalytics.TextAnalyticsClient', return_value=mock_text_analytics):
        client = AzureAIClient(settings)
        
        text = "This is great!"
        
        result = await client.analyze_sentiment(text)
        
        assert result == "positive"
        mock_text_analytics.analyze_sentiment.assert_called_once_with([text])

@pytest.mark.asyncio
async def test_prompt_loading(settings, mock_azure_openai):
    """Test prompt loading from files."""
    with patch('openai.AzureOpenAI', return_value=mock_azure_openai):
        client = AzureAIClient(settings)
        
        # Test with PR review
        pr_diff = "test diff"
        repo_context = "test context"
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "test prompt"
            result = await client.review_pr(pr_diff, repo_context)
            
            assert result == "AI generated response"
            assert mock_open.called
            assert "prompts/pr_review.md" in mock_open.call_args[0][0] 