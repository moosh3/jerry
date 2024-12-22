"""GitHub integration client."""

import logging
import re
from typing import Dict, Any, List
from github import GithubIntegration, Github
from devx.core.config import Settings

logger = logging.getLogger(__name__)

class GitHubClient:
    """Client for interacting with GitHub Enterprise."""

    def __init__(self, settings: Settings):
        """Initialize the GitHub client."""
        self.integration = GithubIntegration(
            settings.github_app_id,
            settings.github_private_key
        )
        self.enterprise_url = settings.github_enterprise_url

    async def get_installation_client(self, installation_id: int) -> Github:
        """Get an authenticated client for a specific installation."""
        access_token = self.integration.get_access_token(installation_id).token
        return Github(
            base_url=self.enterprise_url,
            login_or_token=access_token
        )

    async def get_pr_files(self, installation_id: int, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get detailed information about files changed in a PR."""
        gh = await self.get_installation_client(installation_id)
        repo = gh.get_repo(repo_name)
        pull = repo.get_pull(pr_number)
        
        files_info = []
        for file in pull.get_files():
            file_info = {
                'filename': file.filename,
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'patch': file.patch if file.patch else '',
                'contents': None
            }
            
            if file.status != 'removed' and file.changes < 1000:
                try:
                    contents = repo.get_contents(file.filename, ref=pull.head.sha)
                    file_info['contents'] = contents.decoded_content.decode('utf-8')
                except Exception as e:
                    logger.warning(f"Could not get contents for {file.filename}: {e}")
            
            files_info.append(file_info)
        
        return files_info

    async def get_repo_context(self, installation_id: int, repo_name: str, pr_files: List[Dict[str, Any]]) -> str:
        """Get comprehensive context about the repository and PR changes."""
        gh = await self.get_installation_client(installation_id)
        repo = gh.get_repo(repo_name)
        
        context_parts = []
        
        # Basic repo info
        context_parts.append(f"Repository: {repo.name}")
        if repo.description:
            context_parts.append(f"Description: {repo.description}")
        
        # README content
        try:
            readme = repo.get_readme()
            context_parts.append(f"README:\n{readme.decoded_content.decode()}")
        except Exception as e:
            logger.warning(f"Could not get README for {repo_name}: {e}")
        
        # Get relevant documentation
        docs_path = "docs"
        try:
            contents = repo.get_contents(docs_path)
            relevant_docs = []
            for content in contents:
                if content.type == "file" and content.name.endswith(('.md', '.rst')):
                    for pr_file in pr_files:
                        if any(part.lower() in content.name.lower() 
                              for part in pr_file['filename'].split('/')):
                            doc_content = content.decoded_content.decode()
                            relevant_docs.append(f"Documentation ({content.name}):\n{doc_content}")
            if relevant_docs:
                context_parts.append("\nRelevant Documentation:\n" + "\n".join(relevant_docs))
        except Exception as e:
            logger.warning(f"Could not get documentation: {e}")
        
        return "\n\n".join(context_parts)

    async def comment_on_pr(self, installation_id: int, repo_name: str, pr_number: int, comment: str) -> None:
        """Add a review comment to a pull request."""
        gh = await self.get_installation_client(installation_id)
        repo = gh.get_repo(repo_name)
        pull = repo.get_pull(pr_number)
        pull.create_issue_comment(comment)

    async def handle_pr_event(self, event: Dict[str, Any]) -> None:
        """Handle various PR events and update JIRA accordingly."""
        try:
            action = event.get('action')
            pr = event.get('pull_request', {})
            
            if not pr:
                logger.warning("No pull request data in event")
                return

            installation_id = event['installation']['id']
            repo_name = event['repository']['full_name']
            pr_number = pr['number']
            pr_url = pr['html_url']
            pr_description = pr.get('body', '')

            # Update JIRA tickets based on PR action
            from devx.api.app import app  # Avoid circular import
            await app.state.jira.handle_pr_event(pr_url, action, pr_description)

            # If PR is opened or synchronized, perform review
            if action in ['opened', 'synchronize']:
                logger.info(f"Reviewing PR {pr_number} in {repo_name}")
                
                # Get PR files and context
                pr_files = await self.get_pr_files(installation_id, repo_name, pr_number)
                repo_context = await self.get_repo_context(installation_id, repo_name, pr_files)

                # Prepare diff information
                diff_info = []
                for file in pr_files:
                    diff_info.append(f"File: {file['filename']}")
                    diff_info.append(f"Status: {file['status']}")
                    diff_info.append(f"Changes: +{file['additions']}/-{file['deletions']}")
                    if file['patch']:
                        diff_info.append("Diff:\n" + file['patch'])
                    if file['contents']:
                        diff_info.append("Full contents:\n" + file['contents'])
                    diff_info.append("-" * 40)

                # Get AI review
                review = await app.state.ai.review_pr(
                    "\n".join(diff_info),
                    repo_context
                )

                # Add review comment
                await self.comment_on_pr(installation_id, repo_name, pr_number, review)
                logger.info(f"Added review comment to PR {pr_number}")

        except Exception as e:
            logger.error(f"Error handling PR event: {e}", exc_info=True)
            raise

    async def handle_pr_comment(self, event: Dict[str, Any]) -> None:
        """Handle PR comment events."""
        try:
            comment_body = event['comment']['body'].strip().lower()
            if not comment_body.startswith('/devx review'):
                logger.info("Ignoring non-review comment")
                return

            installation_id = event['installation']['id']
            repo_name = event['repository']['full_name']
            pr_number = event['issue']['number']

            logger.info(f"Processing review request for PR {pr_number} in {repo_name}")

            pr_files = await self.get_pr_files(installation_id, repo_name, pr_number)
            repo_context = await self.get_repo_context(installation_id, repo_name, pr_files)

            diff_info = []
            for file in pr_files:
                diff_info.append(f"File: {file['filename']}")
                diff_info.append(f"Status: {file['status']}")
                diff_info.append(f"Changes: +{file['additions']}/-{file['deletions']}")
                if file['patch']:
                    diff_info.append("Diff:\n" + file['patch'])
                if file['contents']:
                    diff_info.append("Full contents:\n" + file['contents'])
                diff_info.append("-" * 40)

            from devx.api.app import app
            review = await app.state.ai.review_pr(
                "\n".join(diff_info),
                repo_context
            )

            await self.comment_on_pr(installation_id, repo_name, pr_number, review)
            logger.info(f"Added review comment to PR {pr_number}")

        except Exception as e:
            logger.error(f"Error handling PR comment: {e}", exc_info=True)
            raise