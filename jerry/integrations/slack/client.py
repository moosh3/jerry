"""Slack integration using Bolt framework."""

import logging
import re
from typing import Callable, Any, Dict
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from jira.exceptions import JIRAError
from github.GithubException import GithubException
from jerry.core.config import Settings

logger = logging.getLogger(__name__)

class SlackError(Exception):
    """Base exception for Slack-related errors."""
    pass

class CommandError(SlackError):
    """Error in command parsing or execution."""
    pass

class SlackClient:
    """Client for interacting with Slack using Bolt framework."""

    def __init__(self, settings: Settings):
        """Initialize the Slack Bolt app."""
        self.app = App(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret
        )
        self.handler = SlackRequestHandler(self.app)
        self._setup_command_handlers()
        self._setup_error_handlers()

    def _setup_error_handlers(self):
        """Set up global error handlers for the Slack app."""
        
        @self.app.error
        async def global_error_handler(error, body, logger):
            """Handle any unhandled errors in the Slack app."""
            logger.error(f"Error in Slack app: {error}", exc_info=True)
            
            # Get the channel from the event body
            channel = body.get("channel", {}).get("id") or body.get("channel_id")
            if not channel:
                logger.error("Could not determine channel for error message")
                return

            error_message = self._format_error_message(error)
            await self.app.client.chat_postMessage(
                channel=channel,
                text=error_message
            )

    def _format_error_message(self, error: Exception) -> str:
        """Format error messages based on exception type."""
        if isinstance(error, JIRAError):
            if error.status_code == 404:
                return "❌ JIRA ticket not found. Please check the ticket ID and try again."
            elif error.status_code == 403:
                return "❌ Permission denied. I don't have access to perform this action in JIRA."
            else:
                return f"❌ JIRA error: {error.text}"
        
        elif isinstance(error, GithubException):
            if error.status == 404:
                return "❌ GitHub repository or PR not found. Please check the URL and try again."
            elif error.status == 403:
                return "❌ Permission denied. I don't have access to the GitHub repository."
            else:
                return f"❌ GitHub error: {error.data.get('message', str(error))}"
        
        elif isinstance(error, CommandError):
            return f"❌ Command error: {str(error)}"
        
        return "❌ An unexpected error occurred. The development team has been notified."

    async def _validate_ticket_id(self, ticket_id: str) -> str:
        """Validate JIRA ticket ID format."""
        if not re.match(r'^[A-Z]+-\d+$', ticket_id):
            raise CommandError(f"Invalid ticket ID format: {ticket_id}. Expected format: PROJ-123")
        return ticket_id

    async def _validate_pr_url(self, pr_url: str) -> Dict[str, str]:
        """Validate and parse GitHub PR URL."""
        # Match both github.com and enterprise URLs
        pattern = r'https?://(?:github\.com|[^/]+/github)/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.match(pattern, pr_url)
        if not match:
            raise CommandError(
                "Invalid PR URL format. Expected: https://github.com/owner/repo/pull/number"
            )
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'number': match.group(3)
        }

    def _setup_command_handlers(self):
        """Set up all command handlers for the Slack app."""
        
        @self.app.command("/devx")
        async def handle_devx_command(ack, command, say, body):
            """Handle the /devx command with various subcommands."""
            await ack()
            try:
                cmd_parts = command['text'].strip().split(maxsplit=1)
                subcommand = cmd_parts[0] if cmd_parts else ""
                
                handlers = {
                    "create": self._handle_create_ticket,
                    "close": self._handle_close_ticket,
                    "update": self._handle_update_ticket,
                    "review": self._handle_review_pr,
                    "help": self._handle_help
                }
                
                handler = handlers.get(subcommand, self._handle_unknown_command)
                await handler(say, command, body)
                
            except Exception as e:
                logger.error(f"Error handling command: {e}", exc_info=True)
                error_message = self._format_error_message(e)
                await say(error_message)

    async def _handle_create_ticket(self, say, command, body):
        """Handle ticket creation flow."""
        try:
            await say({
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "Let's create a new ticket! Please provide the following information:"}
                    },
                    {
                        "type": "input",
                        "block_id": "ticket_title",
                        "label": {"type": "plain_text", "text": "Ticket Title"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "title_input",
                            "min_length": 5,
                            "max_length": 255
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "ticket_description",
                        "label": {"type": "plain_text", "text": "Description"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "description_input",
                            "multiline": True,
                            "min_length": 10
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Create Ticket"},
                                "action_id": "create_ticket_submit",
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Cancel"},
                                "action_id": "create_ticket_cancel",
                                "style": "danger"
                            }
                        ]
                    }
                ]
            })
        except Exception as e:
            logger.error(f"Error creating ticket form: {e}", exc_info=True)
            await say("❌ Sorry, I couldn't create the ticket form. Please try again later.")

    async def _handle_close_ticket(self, say, command, body):
        """Handle ticket closing flow."""
        try:
            args = command['text'].split()[1:] if len(command['text'].split()) > 1 else []
            
            if not args:
                raise CommandError("Please provide a ticket ID: `/devx close ticket PROJ-123`")
                
            ticket_id = await self._validate_ticket_id(args[0])
            
            # Verify ticket exists before showing form
            from devx.api.app import app
            await app.state.jira.get_issue(ticket_id)
            
            await say({
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"Please provide a reason for closing ticket *{ticket_id}*:"}
                    },
                    {
                        "type": "input",
                        "block_id": "close_reason",
                        "label": {"type": "plain_text", "text": "Reason"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "reason_input",
                            "multiline": True,
                            "min_length": 10
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Close Ticket"},
                                "action_id": "close_ticket_submit",
                                "value": ticket_id,
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Cancel"},
                                "action_id": "close_ticket_cancel",
                                "style": "danger"
                            }
                        ]
                    }
                ]
            })
        except Exception as e:
            logger.error(f"Error in close ticket flow: {e}", exc_info=True)
            error_message = self._format_error_message(e)
            await say(error_message)

    async def _handle_update_ticket(self, say, command, body):
        """Handle ticket updating flow."""
        try:
            parts = command['text'].split(maxsplit=2)
            if len(parts) < 3:
                raise CommandError("Please use the format: `/devx update ticket PROJ-123 Your comment here`")
                
            ticket_id = await self._validate_ticket_id(parts[1])
            comment = parts[2]
            
            if len(comment.strip()) < 10:
                raise CommandError("Comment must be at least 10 characters long")
            
            # Update the ticket using JIRA client
            from devx.api.app import app
            await app.state.jira.add_comment(ticket_id, comment)
            await say(f"✅ Added comment to ticket {ticket_id}")
            
        except Exception as e:
            logger.error(f"Error updating ticket: {e}", exc_info=True)
            error_message = self._format_error_message(e)
            await say(error_message)

    async def _handle_review_pr(self, say, command, body):
        """Handle PR review flow."""
        try:
            await say({
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "I'll help you review a PR. Please provide the following:"}
                    },
                    {
                        "type": "input",
                        "block_id": "pr_url",
                        "label": {"type": "plain_text", "text": "Pull Request URL"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "pr_url_input",
                            "placeholder": {"type": "plain_text", "text": "https://github.com/owner/repo/pull/123"}
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Review PR"},
                                "action_id": "review_pr_submit",
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Cancel"},
                                "action_id": "review_pr_cancel",
                                "style": "danger"
                            }
                        ]
                    }
                ]
            })
        except Exception as e:
            logger.error(f"Error creating PR review form: {e}", exc_info=True)
            await say("❌ Sorry, I couldn't create the PR review form. Please try again later.")

    # Action handlers for interactive components
    async def _setup_action_handlers(self):
        """Set up handlers for interactive components."""
        
        @self.app.action(re.compile(".*_cancel"))
        async def handle_cancel(ack, body, say):
            """Handle cancellation of any action."""
            await ack()
            await say("❌ Action cancelled.")
        
        @self.app.action("create_ticket_submit")
        async def handle_ticket_creation(ack, body, say):
            await ack()
            try:
                values = body['state']['values']
                title = values['ticket_title']['title_input']['value']
                description = values['ticket_description']['description_input']['value']
                
                if len(title.strip()) < 5:
                    raise CommandError("Title must be at least 5 characters long")
                if len(description.strip()) < 10:
                    raise CommandError("Description must be at least 10 characters long")
                
                # Create ticket using JIRA client
                from devx.api.app import app
                ticket = await app.state.jira.create_ticket(title, description)
                await say(f"✅ Created ticket {ticket.key}")
                
            except Exception as e:
                logger.error(f"Error creating ticket: {e}", exc_info=True)
                error_message = self._format_error_message(e)
                await say(error_message)

        @self.app.action("close_ticket_submit")
        async def handle_ticket_closing(ack, body, say):
            await ack()
            try:
                ticket_id = body['actions'][0]['value']
                reason = body['state']['values']['close_reason']['reason_input']['value']
                
                if len(reason.strip()) < 10:
                    raise CommandError("Closing reason must be at least 10 characters long")
                
                # Close ticket using JIRA client
                from devx.api.app import app
                await app.state.jira.close_ticket(ticket_id, reason)
                await say(f"✅ Closed ticket {ticket_id}")
                
            except Exception as e:
                logger.error(f"Error closing ticket: {e}", exc_info=True)
                error_message = self._format_error_message(e)
                await say(error_message)

        @self.app.action("review_pr_submit")
        async def handle_pr_review(ack, body, say):
            await ack()
            try:
                values = body['state']['values']
                pr_url = values['pr_url']['pr_url_input']['value']
                
                # Validate and parse PR URL
                pr_info = await self._validate_pr_url(pr_url)
                
                await say(f"🔍 Reviewing PR #{pr_info['number']} in {pr_info['owner']}/{pr_info['repo']}...")
                
                # Review PR using GitHub client
                from devx.api.app import app
                review = await app.state.github.review_pr(
                    pr_info['owner'],
                    pr_info['repo'],
                    int(pr_info['number'])
                )
                
                await say(f"✅ Review completed! Here's my feedback:\n\n{review}")
                
            except Exception as e:
                logger.error(f"Error reviewing PR: {e}", exc_info=True)
                error_message = self._format_error_message(e)
                await say(error_message)

    def get_handler(self) -> SlackRequestHandler:
        """Get the FastAPI request handler for Slack events."""
        return self.handler