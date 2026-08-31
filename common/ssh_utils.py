import subprocess

def execute_ssh_command(user: str, server: str, port: int, command: str):
    """
    Executes a command on a remote server via SSH.
    Returns (stdout, stderr, returncode).
    """
    ssh_cmd = [
        "ssh",
        "-p", str(port),
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        f"{user}@{server}",
        command
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True
        )
        # Debug logging
        print("DEBUG stdout:", result.stdout)
        print("DEBUG stderr:", result.stderr)
        print("DEBUG returncode:", result.returncode)

        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, str(e), -1
