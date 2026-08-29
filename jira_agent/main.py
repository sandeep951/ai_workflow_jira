import os

from fastapi import FastAPI, Request, BackgroundTasks
from common.models import JiraWebhookPayload
from common.jira_utils import JiraClient
from common.llm_utils import LLMClient
from common.config import Config
from db_agent.main import DBAgent

app = FastAPI(title="Jira AI Agent Workflow")
jira_client = JiraClient()
llm_client = LLMClient()
db_agent = DBAgent()

@app.on_event("startup")
async def startup_event():
    print("Checking system health...")
    if not await llm_client.check_health():
        print("SYSTEM CRITICAL: LLM (Ollama) is not reachable or model is missing.")
        print("Shutting down server to prevent inconsistent state.")
        os._exit(1)
    
    print("System health check passed. LLM is online and responsive.")

# Transition IDs (These should be configured in Config)
TRANSITION_TO_DO = "11" 
TRANSITION_IN_PROGRESS = "21"
TRANSITION_CLOSED = "51"
TRANSITION_REVIEW = "31"

async def process_jira_webhook(payload: JiraWebhookPayload):
    # Convert Pydantic model to dictionary to use .get()
    payload_dict = payload.model_dump()
    
    # 1. Event Gatekeeper: Only process issue creation, updates, or new comments
    event_type = payload_dict.get("webhookEvent", "")
    if event_type not in ["jira:issue_created", "jira:issue_updated", "comment_created"]:
        return


    issue_data = payload_dict.get('issue', {})
    issue_key = issue_data.get('key')
    fields = issue_data.get('fields', {})
    description = fields.get('description', '')
    
    # Handle Jira's complex status object
    status_obj = fields.get('status', {})
    status_name = status_obj.get('name', '') if isinstance(status_obj, dict) else ''
    
    # 2. State Gatekeeper: Only process if the ticket is in a 'starting' state
    # IMPORTANT: To prevent rework and infinite loops, only trigger if status is exactly 'New' or 'Open'.
    # Once it moves to 'To Do', the DB Agent takes over and this agent should NOT touch it again.
    if status_name not in ["New", "Open"]:
        print(f"Issue {issue_key} is in state '{status_name}'. Only 'New' or 'Open' tickets are processed by Jira AI Agent. Skipping.")
        return

    # Additionally, if it has already transitioned to IN_PROGRESS or REVIEW/CLOSED, don't re-process.
    if status_name in ["In Progress", "Review", "Closed", "To Do"]:
         print(f"Issue {issue_key} is already in a processed or transitioned state ({status_name}). Skipping.")
         return

    # Simplification: In a real scenario, fetch comments via API
    comments = jira_client.get_comments(issue_key)
    
    # 3. Duplicate Response Gatekeeper: Don't respond if the AI already has
    ai_signature = "🤖 AI Agent"
    if any(ai_signature in comment.get('body', '') for comment in comments):
        print(f"Issue {issue_key} already has a response from the AI agent. Skipping to avoid duplicates.")
        return
    
    # Phase 1: Verification
    print(f"🤖 Analyzing request for {issue_key}...")
    analysis = await llm_client.analyze_jira_request(description, comments)
    
    # Safe access to analysis keys using .get() to avoid KeyError
    is_verified = analysis.get("verified", False)
    system_error = analysis.get("system_error", False)
    db_name = analysis.get("db_name", "Unknown")
    sql_query = analysis.get("sql_query", "")
    message = analysis.get("message", "No message provided")

    if system_error:
        # If LLM is down, do NOT move to hold and do NOT post "Invalid SQL" comment
        print(f"❌ System Error for {issue_key}: {message}")
        jira_client.add_comment(issue_key, "🤖 AI Agent is currently unavailable. Our team has been notified. Please wait a moment.")
        return # Stop here, do not transition the ticket

    if is_verified:
        print(f"✅ Request verified for {issue_key}. Querying {db_name}...")
        
        # 1. Ensure ticket is in 'To Do' state FIRST
        # This is critical because the DB Agent verifies this state before running
        print(f"Moving {issue_key} to 'To Do' state...")
        jira_client.update_issue_status(issue_key, TRANSITION_TO_DO) # Transition to To Do
        
        # 2. Combined notification: verification and handover
        jira_client.add_comment(issue_key, f"🤖 Jira AI Agent: {message}\n\nRequest verified. Handing over to DB Agent for execution.")
        
        # 3. DB Agent Execution
        db_result = await db_agent.run_query(db_name, sql_query, issue_key=issue_key)
        
        if db_result["status"] == "success":
            # The DB Agent has already posted the LLM-formatted result as a comment.
            # We only need to handle the final state transition.
            pass
        else:
            # Handle Query Error
            # The DB Agent already posted a formatted LLM error comment, 
            # so we no longer post a duplicate 'Query Execution Error' comment here.
            print(f"⚠️ Query failed for {issue_key}, DB Agent has already posted the error.")
            
    else:
        print(f"🛑 Request rejected for {issue_key}: {message}")
        # Move to Hold state
        # Use the custom message generated by the LLM instead of static text
        jira_client.add_comment(issue_key, f"🤖 AI Agent: {message}")
        print(f"Request for {issue_key} rejected. Leaving ticket for user review.")

@app.post("/webhook/jira")
async def jira_webhook(payload: JiraWebhookPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_jira_webhook, payload)
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
