"""Configuration settings for DevX."""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    # Jira settings
    jira_api_token: str
    jira_api_user: str
    jira_api_endpoint: str

    # GitHub settings
    github_app_id: str
    github_private_key: str
    github_enterprise_url: str = "https://api.github.com"  # Default to public GitHub
    github_webhook_secret: str

    # Slack settings
    slack_bot_token: str
    slack_signing_secret: str

    # Azure AI settings
    azure_api_key: str
    azure_endpoint: str

    class Config:
        """Pydantic config."""
        env_file = ".env" 