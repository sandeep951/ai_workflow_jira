# List of authorized databases that the AI Agent is allowed to query
AUTHORIZED_DATABASES = [
    "app_test"
]

# SSH Connection Details mapped by database name
# This allows the agent to support multiple remote servers/scripts based on the db_name
DB_SSH_CONFIGS = {
    "app_test": {
        "user": "sandeep",
        "server": "localhost",
        "port": "2222",
        "executor": "python3",
        "script_path": "/home/sandeep/db_query.py",
        "extra_args": []
    }
}
