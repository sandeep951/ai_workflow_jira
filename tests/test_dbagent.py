import asyncio
from db_agent.main import DBAgent

async def test():
    agent = DBAgent()
    # Replace 'ISSUE-123' with a real issue key that is in 'To Do' state
    # Replace 'SELECT 1 FROM dual' with a valid query for your DB
    result = await agent.run_query(
        db_name="app_test", 
        query="SELECT * FROM employees;", 
        issue_key="TEM-38" 
    )
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test())