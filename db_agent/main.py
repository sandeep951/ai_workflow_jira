import os
import shlex
from common.jira_utils import JiraClient
from common.config import Config
from common.llm_utils import LLMClient
from common.db_config import DB_SSH_CONFIGS
from common.ssh_utils import execute_ssh_command

class DBAgent:
    def __init__(self):
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
        # Execute query via SSH
        result = self.execute_ssh_query(db_name, query)
        
        # 3. Use LLM to format the result
        formatted_message = await self.llm_client.format_db_result(db_name, query, result)
        
        # 4. Handle CSV Attachment if result was successful
        if result.get('status') == 'success' and result.get('data'):
            import csv
            import tempfile
            import io
            
            # Parse the CSV data from strings into lists of values
            csv_content = "\n".join([result['columns'][0]] + result['data']) if result.get('columns') and isinstance(result['columns'], list) and len(result['columns']) == 1 else ""
            
            # Re-evaluating: the current result['columns'] is a list of header values, 
            # and result['data'] is a list of CSV strings.
            # Let's use a more robust approach:
            all_rows = []
            # Use csv reader to parse the data lines
            reader = csv.reader(io.StringIO("\n".join(result['data'])))
            for row in reader:
                all_rows.append(row)
            
            # The headers are already separated in result['columns']
            headers = result['columns']

            # Create a temporary CSV file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as tmp:
                writer = csv.writer(tmp)
                writer.writerow(headers)
                writer.writerows(all_rows)
                csv_path = tmp.name
            
            try:
                self.jira_client.upload_attachment(issue_key, csv_path)
                # Removed duplicate attachment notification since LLM now includes it in the formatted message
            except Exception as e:
                print(f"DB Agent: Failed to upload CSV: {e}")
            finally:
                if os.path.exists(csv_path):
                    os.remove(csv_path)

        self.jira_client.add_comment(issue_key, formatted_message)
        
        # Close Jira issue regardless of success or failure to end the workflow
        self.jira_client.update_issue_status(issue_key, "51") # Transition to Closed
        
        return result

    def execute_ssh_query(self, db_name: str, query: str):
        """Executes a database query on a remote server via SSH using common ssh_utils."""
        cfg = DB_SSH_CONFIGS.get(db_name)
        if not cfg:
            print(f"DB Agent: No SSH configuration found for database {db_name}")
            return {"status": "error", "message": f"Configuration missing for DB: {db_name}", "data": None}

        # Construct the command and wrap it in sh -c to ensure proper quote handling on the remote shell
        # SQL Query (Arg 1) + Extra Args + Executor (e.g. python3) + Script Path
        extra_args_str = " ".join(cfg.get('extra_args', []))
        extra_args_suffix = f" {extra_args_str}" if extra_args_str else ""
        
        inner_command = f"{cfg['executor']} {cfg['script_path']} '{query}'{extra_args_suffix}"
        remote_command = f"sh -c \"{inner_command}\""
        
        try:
            print(f"DB Agent: Executing remote command via SSH: {remote_command}")
            stdout, stderr, returncode = execute_ssh_command(
                user=cfg['user'],
                server=cfg['server'],
                port=cfg['port'],
                command=remote_command
            )
            
            if returncode == 0:
                # Split stdout into lines
                lines = stdout.strip().split('\n') if stdout else []
                if not lines:
                    return {
                        "status": "success",
                        "data": [],
                        "columns": [],
                        "message": "Query executed successfully, but returned no data."
                    }
                
                # The first line is the CSV header
                columns = lines[0].split(',')
                data = lines[1:]
                
                return {
                    "status": "success",
                    "data": data,
                    "columns": columns,
                    "message": "Query executed successfully via SSH"
                }
            else:
                error_msg = stderr if stderr else stdout
                return {
                    "status": "error",
                    "message": f"SSH Execution Error: {error_msg}",
                    "data": None
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
