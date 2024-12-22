# DevX

DevX is an AI Agent assistant that acts as a member of the Developer Experience team. DevX uses the following services for development:

- Jira
- Github
- Azure AI

DevX is responsible for:

- Refining JIRA tickets with technical context
- Create JIRA tickets based on Slack messages from other team members
- Reviewing PR's in Github, providing feedback and suggestions for improvement
- Responding to Github comments

DevX uses AzureAI for its LLM and tool calling capabilities. 

DevX is deployed as a FastAPI application and can be run locally or in a cloud environment.

It uses a Github App to authenticate with Github Enterprise server.

It connects to on-premise JIRA server using the JIRA REST API.

It can send and respond to Slack messages using the bolt framework.

Github examples:

- User opens a pull request, includes a JIRA ticket number in the description
- User comments on the pull request "/devx review", triggering DevX to review the pull request
- When the pull request is merged, DevX will add a comment to the JIRA ticket with a link to the pull request
- When the pull request is closed, DevX will add a comment to the JIRA ticket with the reason for closing
- When the pull request is updated, DevX will add a comment to the JIRA ticket with the reason for updating


Slack examples:

## Github
- User sends the message "/devx create ticket"
    - DevX responds and asks for more information
    - User provides more information
    - DevX creates a JIRA ticket
- User sends the message "/devx close ticket {ticket_id}"
    - DevX closes the JIRA ticket and adds a comment to the ticket with the reason for closing
- User sends the message "/devx update ticket {ticket_id} {comment}"
    - DevX adds a comment to the JIRA ticket

## Jira
- User sends the message "/devx review"
    - DevX asks for which repository the PR is in, and asks for a link to the PR
    - DevX reviews the PR, provides feedback and suggestions for improvement
    - DevX adds a comment to the PR with the feedback and suggestions for improvement
- User sends the message "/devx close ticket"
    - DevX asks for which repository the PR is in, and asks for a link to the PR
    - DevX closes the PR
- User sends the message "/devx update ticket"
    - DevX asks for which repository the PR is in, and asks for a link to the PR
    - DevX updates the PR
