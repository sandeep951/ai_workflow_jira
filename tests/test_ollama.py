import aiohttp
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in the parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

async def check_ollama():
    import os
    base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434").rstrip('/')
    primary_model = os.getenv("LLM_MODEL")
    
    print(f"--- Testing Ollama Connection ---")
    print(f"Target URL: {base_url}/api/tags")
    print(f"Expected Model: {primary_model}")
    print(f"---------------------------------")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/tags", timeout=10) as resp:
                if resp.status != 200:
                    print(f"❌ ERROR: Ollama returned status {resp.status}")
                    return

                data = await resp.json()
                models = [m['name'] for m in data.get('models', [])]
                print(f"✅ SUCCESS: Connected to Ollama.")
                print(f"Available models found: {len(models)}")
                
                if primary_model in models:
                    print(f"✅ SUCCESS: Model '{primary_model}' is installed and ready.")
                else:
                    print(f"❌ ERROR: Model '{primary_model}' NOT found in Ollama.")
                    print(f"Available models list: {models}")

    except Exception as e:
        print(f"❌ ERROR: Could not connect to Ollama. Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama())
