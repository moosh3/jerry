"""JIRA integration client."""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
from jira import JIRA
from jerry.core.config import Settings

logger = logging.getLogger(__name__)

class JiraClient:
    """Client for interacting with JIRA."""

    def __init__(self, settings: Settings):
        """Initialize the JIRA client."""
        self.client = JIRA(
            server=settings.jira_api_endpoint,
            basic_auth=(settings.jira_api_user, settings.jira_api_token)
        )

    async def get_issue(self, ticket_id: str) -> Any:
        """Get a JIRA issue by ID."""
        return self.client.issue(ticket_id)

    async def create_ticket(self, title: str, description: str, issue_type: str = "Task") -> Any:
        """Create a new JIRA ticket."""
        fields = {
            'project': {'key': self._extract_project_key(title)},
            'summary': title,
            'description': description,
            'issuetype': {'name': issue_type}
        }
        return self.client.create_issue(fields=fields)

    async def close_ticket(self, ticket_id: str, reason: str) -> None:
        """Close a JIRA ticket with a reason."""
        issue = await self.get_issue(ticket_id)
        
        # Add comment about closure
        self.client.add_comment(
            issue,
            f"Ticket closed with reason:\n{reason}"
        )
        
        # Transition to "Done" status
        transitions = self.client.transitions(issue)
        done_transition = next(
            (t for t in transitions if t['name'].lower() in ['done', 'closed', 'complete']),
            None
        )
        
        if done_transition:
            self.client.transition_issue(issue, done_transition['id'])
        else:
            logger.error(f"Could not find 'Done' transition for ticket {ticket_id}")
            raise ValueError("Could not find appropriate transition to close ticket")

    async def add_comment(self, ticket_id: str, comment: str) -> None:
        """Add a comment to a JIRA ticket."""
        issue = await self.get_issue(ticket_id)
        self.client.add_comment(issue, comment)

    async def link_pr_to_ticket(self, ticket_id: str, pr_url: str, action: str) -> None:
        """Link a PR to a JIRA ticket with specific action context."""
        issue = await self.get_issue(ticket_id)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = f"Pull Request {action} at {timestamp}\n{pr_url}"
        
        if action == "opened":
            comment = (
                f"🔍 New Pull Request opened at {timestamp}\n"
                f"Link: {pr_url}\n"
                f"Status: In Review"
            )
        elif action == "merged":
            comment = (
                f"✅ Pull Request merged at {timestamp}\n"
                f"Link: {pr_url}\n"
                f"Status: Changes merged to target branch"
            )
        elif action == "closed":
            comment = (
                f"❌ Pull Request closed without merging at {timestamp}\n"
                f"Link: {pr_url}\n"
                f"Status: Closed"
            )
        elif action == "updated":
            comment = (
                f"📝 Pull Request updated at {timestamp}\n"
                f"Link: {pr_url}\n"
                f"Status: Changes pushed to PR"
            )
        
        await self.add_comment(ticket_id, comment)

    async def update_ticket_status(self, ticket_id: str, status: str, comment: Optional[str] = None) -> None:
        """Update a ticket's status with an optional comment."""
        issue = await self.get_issue(ticket_id)
        
        # Add comment if provided
        if comment:
            self.client.add_comment(issue, comment)
        
        # Find the transition
        transitions = self.client.transitions(issue)
        target_transition = next(
            (t for t in transitions if t['name'].lower() == status.lower()),
            None
        )
        
        if target_transition:
            self.client.transition_issue(issue, target_transition['id'])
        else:
            logger.error(f"Could not find '{status}' transition for ticket {ticket_id}")
            raise ValueError(f"Could not find transition to '{status}' status")

    async def extract_ticket_ids_from_text(self, text: str) -> list[str]:
        """Extract JIRA ticket IDs from text using regex."""
        # Match patterns like "PROJECT-123" or "#PROJECT-123"
        pattern = r'(?:^|\s|#)([A-Z]+-\d+)'
        matches = re.finditer(pattern, text)
        return [match.group(1) for match in matches]

    async def handle_pr_event(self, pr_url: str, action: str, description: str) -> None:
        """Handle PR events and update linked JIRA tickets."""
        # Extract ticket IDs from PR description
        ticket_ids = await self.extract_ticket_ids_from_text(description)
        
        if not ticket_ids:
            logger.info(f"No JIRA tickets found in PR description: {pr_url}")
            return
        
        # Update each linked ticket
        for ticket_id in ticket_ids:
            try:
                await self.link_pr_to_ticket(ticket_id, pr_url, action)
                
                # Update ticket status based on PR action
                if action == "opened":
                    await self.update_ticket_status(
                        ticket_id,
                        "In Review",
                        "PR opened for review"
                    )
                elif action == "merged":
                    await self.update_ticket_status(
                        ticket_id,
                        "Done",
                        "PR merged successfully"
                    )
                
            except Exception as e:
                logger.error(f"Error updating ticket {ticket_id} for PR {pr_url}: {e}")

    def _extract_project_key(self, title: str) -> str:
        """Extract project key from ticket title or use default."""
        # Try to extract project key from title (e.g., "[PROJECT] Title")
        match = re.match(r'\[([A-Z]+)\]', title)
        if match:
            return match.group(1)
        
        # Default to a configured project key
        return "DEVX"  # You might want to make this configurable

    async def get_ticket_status(self, ticket_id: str) -> str:
        """Get the current status of a ticket."""
        issue = await self.get_issue(ticket_id)
        return issue.fields.status.name

    async def get_linked_prs(self, ticket_id: str) -> list[str]:
        """Get all PRs linked to a ticket by scanning comments."""
        issue = await self.get_issue(ticket_id)
        prs = []
        
        # Scan comments for PR URLs
        for comment in self.client.comments(issue):
            # Match GitHub PR URLs
            pr_urls = re.findall(
                r'https?://(?:github\.com|[^/]+/github)/[^/]+/[^/]+/pull/\d+',
                comment.body
            )
            prs.extend(pr_urls)
        
        return list(set(prs))  # Remove duplicates 