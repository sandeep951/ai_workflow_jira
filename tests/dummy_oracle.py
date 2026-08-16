import sqlite3
import os

class DummyOracleDB:
    """
    A dummy DB that uses SQLite to simulate an Oracle environment.
    This allows the DB Agent to run real SQL queries against a local file.
    """
    def __init__(self, db_name="dummy_oracle.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        # Create some dummy tables to simulate Oracle data
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, city TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, product TEXT, amount REAL)")
        
        # Insert dummy data
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM orders")
        users = [
            (1, 'Alice', 'alice@example.com', 'New York'),
            (2, 'Bob', 'bob@example.com', 'London'),
            (3, 'Charlie', 'charlie@example.com', 'Tokyo')
        ]
        orders = [
            (101, 1, 'Laptop', 1200.00),
            (102, 1, 'Mouse', 25.00),
            (103, 2, 'Keyboard', 75.00),
            (104, 3, 'Monitor', 300.00)
        ]
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", users)
        cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
        conn.commit()
        conn.close()

    def execute_query(self, query: str):
        # Simple Oracle -> SQLite syntax translation for basic SELECTs
        # In a real mock, we might handle Oracle-specific keywords
        query = query.replace("FROM dual", "") 
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            results = cursor.fetchall()
            conn.close()
            return {"status": "success", "columns": columns, "data": results}
        except Exception as e:
            conn.close()
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    db = DummyOracleDB()
    print("Dummy DB initialized.")
    res = db.execute_query("SELECT * FROM users WHERE id = 1")
    print(f"Test Query Result: {res}")
