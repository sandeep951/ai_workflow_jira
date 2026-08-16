import os
from pathlib import Path
from dotenv import load_dotenv

# Force load .env from the absolute project root directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

print(f"--- DEBUG: Loading Config from {env_path} ---")
print(f"JIRA_URL: {os.getenv('JIRA_URL')}")
print(f"LLM_MODEL: {os.getenv('LLM_MODEL')}")
print(f"LLM_FALLBACK: {os.getenv('LLM_MODEL_FALLBACK')}")
print("-----------------------------")

class Config:
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_MODEL_PRIMARY = os.getenv("LLM_MODEL")
    LLM_MODEL_FALLBACK = os.getenv("LLM_MODEL_FALLBACK")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else None
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
