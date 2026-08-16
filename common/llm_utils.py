import aiohttp
import asyncio
import json
from common.config import Config
from common.db_config import AUTHORIZED_DATABASES

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
                
                # 2. Smoke Test: Verify the model actually responds to a simple prompt
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.primary_model, "prompt": "hi", "stream": False},
                    timeout=self.timeout
                ) as resp:
                    if resp.status != 200:
                        print(f"CRITICAL: Model {self.primary_model} is installed but failed to respond. Status: {resp.status}")
                        return False
                    return True
        except Exception as e:
            print(f"CRITICAL: Could not connect to Ollama at {self.base_url}. Error: {e}")
            
            # Try with fallback model if primary failed (skip for health check - just connectivity test)

    async def verify_server_ready(self):
        """Minimal startup verification - checks API and model availability without prompting."""
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Verify server endpoint is reachable AND returns valid JSON response structure for /api/tags
                async with session.get(f"{self.base_url}/api/version", timeout=self.timeout) as resp:
                    if resp.status != 200:
                        print(f"CRITICAL: Cannot reach Ollama at {self.base_url}. Status: {resp.status}")
                        return False
                    
                    # Minimal version check just ensures endpoint is responsive, no prompt cost
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
                
                # 4. Minimal smoke test - just a simple response without expecting JSON from LLM itself since we only want connection verification at startup 
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.primary_model, "prompt": "hi", "stream": False},
                    timeout=self.timeout
                ) as resp:
                    if resp.status != 200:
                        print(f"CRITICAL: Model {self.primary_model} is installed but failed to respond. Status: {resp.status}")
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
                continue

        return {
            "verified": False,
            "system_error": True,
            "db_name": "",
            "sql_query": "",
            "message": "All available LLM models failed to respond."
        }

    async def _call_ollama(self, model: str, description: str, comments: list):
        # Extract only the body text from comments to reduce noise
        comment_texts = [c.get('body', '') if isinstance(c, dict) else str(c) for c in comments]
        formatted_comments = "\n".join([f"- {text}" for text in comment_texts])

        prompt = (
            f"Analyze the following Jira request. Look for the SQL query and Database name across BOTH the description and the comments.\n\n"
            f"Description: {description}\n"
            f"Comments:\n{formatted_comments}\n\n"
            f"You are an authorized SQL Agent. "
            f"Authorized Databases: {', '.join(AUTHORIZED_DATABASES)}\n\n"
            f"1. If the request is a greeting (e.g., 'Hi', 'Hello'), respond with a friendly welcome message "
            f"introducing yourself as the Jira SQL Agent and set 'verified' to false.\n"
            f"2. If the request is a DB query, extract the DB name and SQL query. "
            f"The user might provide the DB name in the description and the SQL in a comment, or vice versa. Combine all available information.\n"
            f"Check if the DB name is one of the authorized ones listed above. "
            f"Check if it is a SELECT query and if it contains a WHERE clause for safety. "
            f"If DB is authorized, query is SELECT, and WHERE is present, set 'verified' to true. "
            f"Otherwise, set 'verified' to false and write a polite explanation of what is missing or why it was rejected.\n\n"
            f"You MUST respond ONLY with a valid raw JSON object. "
            f"Do NOT include any conversational text, explanations, or markdown code blocks. "
            f"Required keys: 'verified', 'db_name', 'sql_query', 'message'."
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
