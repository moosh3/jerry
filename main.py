"""Main entry point for DevX application."""

import logging
import uvicorn
from devx.api.app import create_app
from devx.core.config import Settings
from devx.integrations.jira.client import JiraClient
from devx.integrations.github.client import GitHubClient
from devx.integrations.slack.client import SlackClient
from devx.integrations.azureai.client import AzureAIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize and run the DevX application."""
    # Load settings from environment
    settings = Settings()
    
    # Initialize clients
    jira_client = JiraClient(settings)
    github_client = GitHubClient(settings)
    slack_client = SlackClient(settings)
    ai_client = AzureAIClient(settings)
    
    # Create FastAPI app
    app = create_app(settings)
    
    # Make clients available to the app
    app.state.jira = jira_client
    app.state.github = github_client
    app.state.slack = slack_client
    app.state.ai = ai_client
    
    logger.info("Starting DevX application...")
    
    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload during development
    )

if __name__ == "__main__":
    main() 