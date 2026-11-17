"""Bad example: shell=True with user input."""

import subprocess


def list_file(user_supplied_name: str) -> str:
    completed = subprocess.run(
        f"ls {user_supplied_name}",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout


# Problem:
# User input is interpreted by the shell. Pass a list of explicit args and avoid shell=True.
