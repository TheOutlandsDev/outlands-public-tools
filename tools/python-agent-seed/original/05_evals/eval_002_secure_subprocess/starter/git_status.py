import subprocess


class GitStatusError(RuntimeError):
    pass


def git_status_short(repo_path):
    return subprocess.check_output(f"cd {repo_path}; git status --short", shell=True).decode()
