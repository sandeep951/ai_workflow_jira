import asyncio
from datetime import datetime, timedelta
from common.jira_utils import JiraClient
from common.llm_utils import LLMClient
from common.config import Config

# Mock DB to track tickets in hold (In production, use Redis or SQL)
HOLD_TICKETS = {} # {issue_key: {"last_reminder": datetime, "created_at": datetime}}

async def cleanup_hold_tickets():
    jira_client = JiraClient()
    llm_client = LLMClient()
    now = datetime.now()
    
    # Note: In a real scenario, we would query Jira API for all tickets in 'Hold' status
    for issue_key, info in list(HOLD_TICKETS.items()):
        # 1. Check for updates
        details = jira_client.get_issue_details(issue_key)
        description = details.get('fields', {}).get('description', '')
        
        analysis = await llm_client.analyze_jira_request(description, [])
        if analysis["verified"]:
            jira_client.add_comment(issue_key, "✅ Description updated and verified. Moving to In Progress.")
            jira_client.update_issue_status(issue_key, "102") # Transition to In Progress
            del HOLD_TICKETS[issue_key]
            continue

        # 2. 24hr Reminder
        if now - info["last_reminder"] >= timedelta(hours=24):
            jira_client.add_comment(issue_key, "🔔 Reminder: Your ticket is still on hold. Please provide a valid DB name and a SELECT query with a WHERE clause.")
            HOLD_TICKETS[issue_key]["last_reminder"] = now

        # 3. 3-day Close
        if now - info["created_at"] >= timedelta(days=3):
            jira_client.add_comment(issue_key, "❌ Closing ticket due to inactivity for 3 days.")
            jira_client.update_issue_status(issue_key, "103") # Transition to Closed
            del HOLD_TICKETS[issue_key]

async def schedule_cleanup():
    while True:
        await cleanup_hold_tickets()
        await asyncio.sleep(3600) # Run every hour
