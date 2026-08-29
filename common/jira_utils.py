import requests
import os
from common.config import Config

class JiraClient:
    def __init__(self):
        self.base_url = Config.JIRA_URL
        self.auth = (Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)

    def add_comment(self, issue_key: str, comment: str):
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }
                ]
            }
        }
        response = requests.post(url, json=payload, auth=self.auth)
        return response.json()

    def update_issue_status(self, issue_key: str, transition_id: str):
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        payload = {"transition": {"id": transition_id}}
        response = requests.post(url, json=payload, auth=self.auth)
        
        # Attempt to get the new status name from the response if possible, 
        # but since transitions usually return 204 No Content, we'll fetch the issue details
        if response.status_code != 204 and response.status_code != 200:
            print(f"ERROR: Failed to transition {issue_key} to {transition_id}. Status: {response.status_code}, Response: {response.text}")
        else:
            issue = self.get_issue_details(issue_key)
            status_name = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
            print(f"SUCCESS: Transitioned {issue_key} to {status_name}")
            
        return response.json() if response.status_code != 204 else {}

    def get_issue_details(self, issue_key: str):
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        response = requests.get(url, auth=self.auth)
        return response.json()

    def get_comments(self, issue_key: str):
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        response = requests.get(url, auth=self.auth)
        if response.status_code == 200:
            return response.json().get('comments', [])
        return []

    def upload_attachment(self, issue_key: str, file_path: str):
        """Uploads a file as an attachment to a Jira issue."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/attachments"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            headers = {'X-Atlassian-Token': 'no-check'}
            response = requests.post(url, files=files, headers=headers, auth=self.auth)
            
        if response.status_code == 200:
            print(f"SUCCESS: Uploaded {file_path} to {issue_key}")
            return response.json()
        else:
            print(f"ERROR: Failed to upload {file_path}. Status: {response.status_code}, Response: {response.text}")
            return None
