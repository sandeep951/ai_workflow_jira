# AI Agent Workflow - Jira SQL Automator

## Project Overview
This project implements an automated workflow using Python and FastAPI to handle Database (DB) query requests coming from Jira tickets. The system uses an LLM to verify request details and a dedicated DB agent to execute queries against an Oracle server.

## Workflow Phases

### Phase 1: Request Intake & Validation
1. **Jira Webhook**: FastAPI receives notifications when a Jira ticket is created or updated.
2. **LLM Verification**:
   - The system reads the Jira description and latest 3 comments.
   - The LLM verifies if the ticket is in 'New' or 'Open' state.
   - The LLM extracts the **DB Name** and **SQL Query**.
3. **Validation Logic**:
   - Ensures the SQL statement is a `SELECT` query.
   - Checks for a `WHERE` clause. If missing, the ticket stays in its current state and a polite explanation is posted as a comment.
4. **Handover**:
   - Valid requests are transitioned to the 'To Do' state.
   - A notification comment is posted confirming verification and handover to the DB Agent.

### Phase 2: Execution & Response
1. **State Verification**: The DB Agent verifies the ticket is in 'To Do' state.
2. **Execution**:
   - Ticket is transitioned to 'In Progress'.
   - DB Agent executes the query against the dummy Oracle DB.
3. **Result Handling**:
   - Raw results are sent back to the LLM to be transformed into a user-friendly response.
   - The professional response is posted as a comment on the Jira ticket.
   - Ticket state is transitioned to 'Closed' (regardless of success or failure to prevent loops).
4. **Notification**:
   - If successful, an email is sent to the user notifying them that the result is ready.

## Technical Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **DB**: Oracle (Dummy Server)
- **LLM**: Ollama (Local LLM)
- **Integrations**: Jira API, Email SMTP

## Installation & Setup

### 1. Prerequisites
- Install [Ollama](https://ollama.ai/)
- Pull required models (e.g., `ollama pull qwen3.5:9b`)

### 2. Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
JIRA_URL=your_jira_url
JIRA_EMAIL=your_email
JIRA_API_TOKEN=your_token
LLM_MODEL=qwen3.5:9b
LLM_MODEL_FALLBACK=gemma4:12b
LLM_BASE_URL=http://127.0.0.1:11434
LLM_TIMEOUT=60
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASS=your_app_password
```

### 4. Running the Server
```bash
uvicorn jira_agent.main:app --reload --host 0.0.0.0 --port 8000
```
