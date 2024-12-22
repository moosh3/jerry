"""FastAPI application for DevX."""

import logging
import hmac
import hashlib
from fastapi import FastAPI, Request, Depends, HTTPException
from jerry.core.config import Settings
from jerry.integrations.slack.client import SlackClient

logger = logging.getLogger(__name__)

async def verify_github_webhook(request: Request, settings: Settings) -> None:
    """Verify that the webhook is from GitHub."""
    if not settings.github_webhook_secret:
        return

    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        raise HTTPException(status_code=401, detail="No signature header")

    body = await request.body()
    hmac_gen = hmac.new(
        settings.github_webhook_secret.encode(),
        msg=body,
        digestmod=hashlib.sha256
    )
    expected_signature = f"sha256={hmac_gen.hexdigest()}"

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

def create_app(settings: Settings) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DevX",
        description="AI Agent for Developer Experience",
        version="0.1.0"
    )

    # Initialize Slack client
    slack = SlackClient(settings)
    
    # GitHub webhook endpoint
    @app.post("/github/webhook")
    async def github_webhook(request: Request):
        # Verify webhook signature
        await verify_github_webhook(request, settings)
        
        # Parse event type
        event_type = request.headers.get('X-GitHub-Event')
        
        # Handle issue_comment events (includes PR comments)
        if event_type == 'issue_comment':
            payload = await request.json()
            
            # Check if this is a PR comment (issues have no pull_request key)
            if 'pull_request' in payload.get('issue', {}):
                await app.state.github.handle_pr_comment(payload)
                return {"message": "PR comment processed"}
            
        return {"message": f"Event type {event_type} ignored"}

    # Slack event handlers
    @slack.message("help")
    async def handle_help_message(message, say, client):
        response = await app.state.ai.generate_slack_response("help")
        await say(response)
    
    @slack.command("/devx")
    async def handle_devx_command(ack, command, say):
        await ack()
        cmd_text = command['text']
        
        if cmd_text.startswith('refine '):
            # Handle JIRA ticket refinement
            ticket_key = cmd_text.split('refine ')[1]
            ticket = await app.state.jira.get_issue(ticket_key)
            refined = await app.state.ai.refine_ticket(
                ticket.fields.description,
                "Technical context will be gathered here"
            )
            await app.state.jira.add_comment(ticket_key, refined)
            await say(f"✅ I've refined ticket {ticket_key} with technical context!")
            
        elif cmd_text.startswith('review '):
            # Handle PR review
            pr_url = cmd_text.split('review ')[1]
            pr_diff = await app.state.github.get_pr_diff(pr_url)
            review = await app.state.ai.review_pr(pr_diff, "Repository context here")
            await say(f"🔍 Here's my review of {pr_url}:\n\n{review}")
            
        else:
            # Generate AI response for unknown commands
            response = await app.state.ai.generate_slack_response(
                cmd_text,
                "Command context: User asked for help with DevX command"
            )
            await say(response)

    # Slack events endpoint
    @app.post("/slack/events")
    async def slack_events(request: Request):
        return await slack.get_handler().handle(request)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    # Store clients in app state
    app.state.slack = slack

    return app