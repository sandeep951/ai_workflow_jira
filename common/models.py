from pydantic import BaseModel
from typing import Any, Dict

class JiraWebhookPayload(BaseModel):
    issue_event: Dict[str, Any] = {}
    issue: Dict[str, Any] = {}
    # Allow extra fields to avoid 422 errors
    model_config = {
        "extra": "allow"
    }

class JiraIssue(BaseModel):
    key: str
    fields: Dict[str, Any]
