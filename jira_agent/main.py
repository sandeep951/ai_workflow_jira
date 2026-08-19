import os

from fastapi import FastAPI, Request, BackgroundTasks
from common.models import JiraWebhookPayload
from common.jira_utils import JiraClient
from common.llm_utils import LLMClient
from common.config import Config
from common.email_utils import EmailClient
from db_agent.main import DBAgent

app = FastAPI(title="Jira AI Agent Workflow")
jira_client = JiraClient()
llm_client = LLMClient()
email_client = EmailClient()
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
TRANSITION_HOLD = "101" 
TRANSITION_IN_PROGRESS = "102"
TRANSITION_CLOSED = "103"
TRANSITION_REVIEW = "104"

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
    # We only want to trigger the AI if the ticket is 'To Do' or 'New'
    if status_name not in ["To Do", "New", "Open"]:
        print(f"Issue {issue_key} is in state '{status_name}'. Skipping processing.")
        return

    # Simplification: In a real scenario, fetch comments via API
    comments = jira_client.get_comments(issue_key)
    
    # 3. Duplicate Response Gatekeeper: Don't respond if the AI already has
    ai_signature = "🤖 AI Agent"
    # If it's a comment event, only process if the LATEST comment isn't from the AI
    if event_type == "comment_created":
        last_comment = comments[-1] if comments else {}
        if ai_signature in last_comment.get('body', ''):
            print(f"Issue {issue_key} latest comment is from AI. Skipping to avoid loop.")
            return
    elif any(ai_signature in comment.get('body', '') for comment in comments):
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
        # Move to Phase 2
        jira_client.add_comment(issue_key, f"🤖 AI Agent: {message}")
        jira_client.update_issue_status(issue_key, TRANSITION_IN_PROGRESS)
        
        # DB Agent Execution
        db_result = db_agent.run_query(db_name, sql_query)
        
        if db_result["status"] == "success":
            # Format the result as a table/text for Jira
            columns = ", ".join(db_result["columns"])
            data_rows = "\n".join([str(row) for row in db_result["data"]])
            formatted_result = f"📊 Query Result:\nColumns: {columns}\nData:\n{data_rows}"
            
            print(f"🚀 Posting results to {issue_key}")
            jira_client.add_comment(issue_key, formatted_result)
            jira_client.update_issue_status(issue_key, TRANSITION_REVIEW)
            
            # Send Email Notification
            user_email = "user@example.com" # In real case, fetch from Jira issue
            email_client.send_email(
                user_email, 
                f"Jira {issue_key} Result Ready", 
                f"The result for your SQL query on {analysis['db_name']} is now available in Jira ticket {issue_key}. Please review and close the ticket."
            )
        else:
            # Handle Query Error
            print(f"⚠️ Query failed for {issue_key}: {db_result['message']}")
            jira_client.add_comment(issue_key, f"❌ Query Execution Error: {db_result['message']}")
            jira_client.update_issue_status(issue_key, TRANSITION_HOLD)
            
    else:
        print(f"🛑 Request rejected for {issue_key}: {message}")
        # Move to Hold state
        # Use the custom message generated by the LLM instead of static text
        jira_client.add_comment(issue_key, f"🤖 AI Agent: {message}")
        jira_client.update_issue_status(issue_key, TRANSITION_HOLD)

@app.post("/webhook/jira")
async def jira_webhook(payload: JiraWebhookPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_jira_webhook, payload)
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
