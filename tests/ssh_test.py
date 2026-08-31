import subprocess

def execute_ssh_command(user: str, server: str, port: int, command: str):
    ssh_cmd = ["ssh", "-p", str(port), f"{user}@{server}", command]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        print("DEBUG stdout:", result.stdout)
        print("DEBUG stderr:", result.stderr)
        print("DEBUG returncode:", result.returncode)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, str(e), -1


if __name__ == "__main__":
    out, err, code = execute_ssh_command(
        user="sandeep",
        server="localhost",
        port=2222,
        command="echo 'Hello from container!'"
    )
    print("stdout:", out)
    print("stderr:", err)
    print("returncode:", code)
