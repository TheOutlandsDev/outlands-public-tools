"""Separate reference repair; only reviewed unittest mocks exercise Git here."""
import subprocess
from pathlib import Path

class GitStatusError(RuntimeError):
    pass

def git_status_short(repo_path: str | Path) -> str:
    try:
        result = subprocess.run(['git', 'status', '--short'], cwd=Path(repo_path), capture_output=True, text=True, check=False)
    except OSError as error:
        raise GitStatusError('Git could not be started') from error
    if result.returncode:
        raise GitStatusError(result.stderr.strip() or 'Git returned an error')
    return result.stdout
