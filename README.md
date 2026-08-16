# AI Agent Workflow - Jira SQL Automator

## Project Overview
This project implements an automated workflow using Python and FastAPI to handle Database (DB) query requests coming from Jira tickets. The system uses an LLM to verify request details and a dedicated DB agent to execute queries against an Oracle server.

## Workflow Phases

### Phase 1: Request Intake & Validation
1. **Jira Webhook**: FastAPI receives notifications when a Jira ticket is created or updated.
2. **LLM Verification**:
   - The system reads the Jira description and comments.
   - The LLM verifies if the ticket is in 'New' state.
   - The LLM extracts the **DB Name** and **SQL Query**.
3. **Validation Logic**:
   - Ensures the SQL statement is a `SELECT` query.
   - Checks for a `WHERE` clause. If missing, the ticket is moved to 'Hold' state, and a comment is added asking for a specific filter.
4. **Hold State Management**:
   - Daily checks for tickets in 'Hold' state.
   - Post a reminder comment every 24 hours.
   - If the user updates the description and it meets criteria, move to Phase 2.
   - If no update for 3 consecutive days, the AI agent closes the Jira ticket.

### Phase 2: Execution & Response
1. **Transition**: Valid requests are moved to 'In Progress' state.
2. **DB Agent Delegation**:
   - The Jira API agent assigns the task to a DB Agent.
   - DB Agent connects to a dummy Oracle DB server and executes the query.
3. **Result Handling**:
   - Query results are sent back to the Jira API agent.
   - Results are posted as a comment on the Jira ticket.
   - Ticket state is moved to 'Review'.
4. **Notification**:
   - An email is sent to the user notifying them that the result is ready.
   - The user is requested to review and close the ticket manually.

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
