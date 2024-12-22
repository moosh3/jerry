"""Azure AI integration client."""

import os
from typing import Any, Dict, List
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from openai import AzureOpenAI
from jerry.core.config import Settings

class AzureAIClient:
    """Client for interacting with Azure AI services."""

    def __init__(self, settings: Settings):
        """Initialize Azure AI clients."""
        self.openai_client = AzureOpenAI(
            api_key=settings.azure_api_key,
            api_version="2023-12-01-preview",
            azure_endpoint=settings.azure_endpoint
        )
        
        self.text_analytics = TextAnalyticsClient(
            endpoint=settings.azure_endpoint,
            credential=AzureKeyCredential(settings.azure_api_key)
        )

    async def analyze_code(self, code: str, prompt: str) -> Dict[str, Any]:
        """Analyze code using Azure OpenAI."""
        response = await self.openai_client.chat.completions.create(
            model="gpt-4",  # Assuming GPT-4 is deployed in your Azure instance
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": code}
            ],
            temperature=0.3,  # Lower temperature for more focused responses
            max_tokens=2000
        )
        return response.choices[0].message.content

    async def refine_ticket(self, description: str, technical_context: str) -> str:
        """Refine a JIRA ticket with technical context."""
        with open("devx/prompts/jira_planning.md", "r") as f:
            prompt = f.read()
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Description: {description}\nTechnical Context: {technical_context}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    async def review_pr(self, pr_diff: str, repo_context: str) -> Dict[str, Any]:
        """Review a pull request."""
        with open("devx/prompts/pr_review.md", "r") as f:
            prompt = f.read()
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"PR Diff:\n{pr_diff}\n\nRepo Context:\n{repo_context}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    async def generate_slack_response(self, message: str, context: str = "") -> str:
        """Generate a response for Slack messages."""
        with open("devx/prompts/slack_responses.md", "r") as f:
            prompt = f.read()
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Message: {message}\nContext: {context}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    async def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text using Azure Text Analytics."""
        response = self.text_analytics.analyze_sentiment([text])[0]
        return response.sentiment 