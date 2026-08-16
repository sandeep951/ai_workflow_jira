from tests.dummy_oracle import DummyOracleDB

class DBAgent:
    def __init__(self):
        self.db = DummyOracleDB()

    def run_query(self, db_name: str, query: str):
        print(f"DB Agent: Connecting to {db_name}...")
        # In a real scenario, db_name would determine which connection string to use
        result = self.db.execute_query(query)
        return result
