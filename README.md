# Jerry

Jerry is an AI-powered Developer Experience assistant that helps streamline development workflows by integrating JIRA, GitHub, and Slack. It acts as a member of your Developer Experience team, handling PR reviews, ticket management, and team communication.

## Features

- 🔍 Automated PR reviews with AI-powered analysis
- 🎫 JIRA ticket management and refinement
- 💬 Slack integration for team communication
- 🔄 Bidirectional sync between JIRA and GitHub
- 🤖 AI-powered technical context generation

[View Full Features List](docs/FEATURES.md)

## Prerequisites

- Python 3.9+
- GitHub Enterprise or github.com account
- JIRA Server/Cloud instance
- Slack workspace
- Azure OpenAI API access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/jerry.git
cd jerry
```

2. Install dependencies using `uv`:
```bash
uv pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
# JIRA Configuration
JIRA_API_TOKEN=your_token
JIRA_API_USER=your_username
JIRA_API_ENDPOINT=https://your-jira-instance.com

# GitHub Configuration
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY=your_private_key
GITHUB_ENTERPRISE_URL=https://github.your-company.com
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your_signing_secret

# Azure AI Configuration
AZURE_API_KEY=your_api_key
AZURE_ENDPOINT=your_endpoint
```

## GitHub App Setup

1. Create a new GitHub App in your organization
2. Configure the following permissions:
   - Pull requests: Read & Write
   - Issues: Read & Write
   - Contents: Read
3. Subscribe to events:
   - Pull request
   - Pull request review
   - Issue comment
4. Install the app in your repositories

## Usage

### Starting the Server

Run the FastAPI server:
```bash
python -m jerry.main
```

The server will start on `http://localhost:8000`.

### Slack Commands

- Create a ticket:
```
/jerry create ticket
```

- Review a PR:
```
/jerry review
```

- Update a ticket:
```
/jerry update ticket PROJ-123 Your comment here
```

### GitHub Integration

- Add a JIRA ticket number to your PR description: `PROJ-123`
- Request a review by commenting: `/jerry review`
- Jerry will automatically:
  - Review new and updated PRs
  - Update linked JIRA tickets
  - Provide technical feedback

## Development

### Project Structure

```
jerry/
├── jerry/
│   ├── api/           # FastAPI application
│   ├── integrations/  # Service integrations
│   │   ├── github/    # GitHub integration
│   │   ├── jira/      # JIRA integration
│   │   ├── slack/     # Slack integration
│   │   └── azureai/   # Azure AI integration
│   ├── core/          # Core functionality
│   └── prompts/       # AI prompt templates
├── docs/              # Documentation
└── tests/             # Test suite
```

### Running Tests

```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please:
1. Check the [documentation](docs/)
2. Open an issue
3. Contact the Jerry team
