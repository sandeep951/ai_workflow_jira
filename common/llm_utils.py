import aiohttp
import asyncio
import json
import traceback
from common.config import Config
from common.db_config import AUTHORIZED_DATABASES
from common.prompts import PROMPTS

class LLMClient:
    def __init__(self):
        self.api_key = Config.LLM_API_KEY
        self.primary_model = Config.LLM_MODEL_PRIMARY
        self.fallback_model = Config.LLM_MODEL_FALLBACK
        self.base_url = Config.LLM_BASE_URL
        self.timeout = Config.LLM_TIMEOUT

    async def check_health(self) -> bool:
        """Checks if Ollama is running, the primary model is available, and it can respond."""
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Verify server is up and model is installed
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                    if resp.status != 200:
                        print(f"CRITICAL: Ollama health check failed with status {resp.status}")
                        return False
                    data = await resp.json()
                    models = [m['name'] for m in data.get('models', [])]
                    if self.primary_model not in models:
                        print(f"CRITICAL: Primary model {self.primary_model} not found. Available: {models}")
                        return False
                return True
        except Exception as e:
            print(f"CRITICAL: Could not connect to Ollama at {self.base_url}. Error: {e}")
            return False

    async def verify_server_ready(self):
        """Minimal startup verification - checks API and model availability without prompting."""
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Verify server endpoint is reachable AND returns valid JSON response structure for /api/version
                async with session.get(f"{self.base_url}/api/version", timeout=self.timeout) as resp:
                    if resp.status != 200:
                        print(f"CRITICAL: Cannot reach Ollama at {self.base_url}. Status: {resp.status}")
                        return False
                    await resp.json()

                # 2. Verify model exists without requiring it to respond - GET /api/tags returns model list
                async with session.get(f"{self.base_url}/api/tags", timeout=self.timeout) as resp:
                    if resp.status != 200:
                        print(f"CRITICAL: Ollama health check failed with status {resp.status}")
                        return False
                    data = await resp.json()
                    models = [m['name'] for m in data.get('models', [])]

                # 3. Verify primary model is installed by checking it appears in the tags response 
                if self.primary_model not in models:
                    print(f"CRITICAL: Primary model {self.primary_model} not found in Ollama. Available models: {models}")
                    return False


        except Exception as e:
            print(f"CRITICAL: Could not connect to Ollama at {self.base_url}. Error: {e}")
            return False

    async def analyze_jira_request(self, description: str, comments: list):
        for model_name in [self.primary_model, self.fallback_model]:
            try:
                return await self._call_ollama(model_name, description, comments)
            except Exception as e:
                print(f"Attempt with {model_name} failed: {e}")
                traceback.print_exc()
                continue

        return {
            "verified": False,
            "system_error": True,
            "db_name": "",
            "sql_query": "",
            "message": "All available LLM models failed to respond."
        }

    async def format_db_result(self, db_name: str, query: str, result: any):
        """Sends the raw DB result to the LLM to be formatted into a user-friendly message."""
        for model_name in [self.primary_model, self.fallback_model]:
            try:
                prompt = PROMPTS["format_db_result"].format(
                    db_name=db_name,
                    query=query,
                    result=result
                )
                response = await self._call_ollama_raw(model_name, prompt)
                
                # Split response into CSV and Comment sections
                if "## Jira Comment" in response:
                    parts = response.split("## Jira Comment")
                    return parts[1].strip()
                
                return response
            except Exception as e:
                print(f"Attempt with {model_name} failed: {e}")
                traceback.print_exc()
                continue
        return f"⚙️ DB Agent: Error formatting result. Raw: {result}"

    async def _call_ollama_raw(self, model: str, prompt: str):
        """Helper to get a raw string response from LLM without JSON parsing."""
        print(f"\n--- DEBUG: Sending Raw Prompt to LLM ({model}) ---\n{prompt}\n--- END DEBUG ---\n")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=self.timeout
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ollama returned status {resp.status}")
                result = await resp.json()
                response_text = result.get("response", "").strip()
                print(f"--- DEBUG: LLM Response ({model}) ---\n{response_text}\n--- END DEBUG ---\n")
                return response_text

    async def _call_ollama(self, model: str, description: str, comments: list):
        # Extract only the body text from the latest 3 comments to reduce noise and tokens
        latest_comments = comments[-3:] if comments else []
        comment_texts = [c.get('body', '') if isinstance(c, dict) else str(c) for c in latest_comments]
        formatted_comments = "\n".join([f"- {text}" for text in comment_texts])

        prompt = PROMPTS["analyze_jira_request"].format(
            description=description,
            formatted_comments=formatted_comments,
            authorized_dbs=", ".join(AUTHORIZED_DATABASES)
        )
        print(f"\n--- DEBUG: Sending Prompt to LLM ({model}) ---\n{prompt}\n--- END DEBUG ---\n")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=self.timeout
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ollama returned status {resp.status}")
                
                result = await resp.json()
                response_text = result.get("response", "").strip()
                
                # Clean markdown code blocks if present
                if response_text.startswith("```"):
                    lines = response_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    response_text = "\n".join(lines).strip()
                
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    # Fallback: if it's not JSON, wrap it in a system error response
                    return {
                        "verified": False,
                        "system_error": True,
                        "db_name": "",
                        "sql_query": "",
                        "message": f"LLM returned invalid JSON format: {response_text[:100]}..."
                    }

