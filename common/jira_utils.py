import requests
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
        return response.json()

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
