from tests.dummy_oracle import DummyOracleDB
from common.jira_utils import JiraClient
from common.config import Config
from common.llm_utils import LLMClient

class DBAgent:
    def __init__(self):
        self.db = DummyOracleDB()
        self.jira_client = JiraClient()
        self.llm_client = LLMClient()

    async def run_query(self, db_name: str, query: str, issue_key: str = None):
        if not issue_key:
            print("DB Agent: No issue key provided. Skipping Jira updates.")
            return self.db.execute_query(query)

        print(f"DB Agent: Processing issue {issue_key}. Verifying state...")
        
        # 1. Verify Jira issue is in 'To Do' state before proceeding
        issue = self.jira_client.get_issue_details(issue_key)
        fields = issue.get('fields', {})
        status_obj = fields.get('status', {})
        status_name = status_obj.get('name', '') if isinstance(status_obj, dict) else ''
        
        if status_name != "To Do":
            print(f"DB Agent: Issue {issue_key} is in state '{status_name}', expected 'To Do'. Aborting execution.")
            return {"status": "error", "message": f"Issue is not in To Do state (current: {status_name})"}

        # 2. Move to In Progress
        # Transition ID for 'In Progress'
        self.jira_client.update_issue_status(issue_key, "21")
        print(f"DB Agent: Moved {issue_key} to In Progress.")
        
        # Removed the "Now processing" comment to prevent double comments
        # as the final result comment is the most important.
        
        print(f"DB Agent: Connecting to {db_name}...")
        # In a real scenario, db_name would determine which connection string to use
        result = self.db.execute_query(query)
        
        # 3. Use LLM to format the result
        formatted_message = await self.llm_client.format_db_result(db_name, query, result)
        self.jira_client.add_comment(issue_key, formatted_message)
        
        # Close Jira issue regardless of success or failure to end the workflow
        self.jira_client.update_issue_status(issue_key, "51") # Transition to Closed
        
        return result
