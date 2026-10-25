"""Create an authored disposable Git repository; no user source is copied."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import git_worktree_report as r


def create(destination, executable):
    target, git = r.local_path(destination), r.local_path(executable)
    r.no_links(target.parent); r.no_links(git)
    r.require(not target.exists() and not target.is_symlink(), 'FRESH_DESTINATION_REQUIRED')
    target.mkdir(mode=0o700)
    def command(*args):
        return subprocess.run([str(git), '-c', 'core.hooksPath=' + os.devnull,
                               '-c', 'user.name=Fictional Example', '-c', 'user.email=example@example.invalid',
                               '-C', str(target), *args], env=r.isolated_environment(),
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=True, timeout=15)
    command('init', '--initial-branch=main')
    (target / 'README.md').write_text('# Fictional source only\n', encoding='utf-8')
    (target / 'staged.txt').write_text('Fictional original\n', encoding='utf-8')
    command('add', 'README.md', 'staged.txt'); command('commit', '-m', 'Fictional fixture baseline')
    (target / 'README.md').write_text('# Fictional modified source\n', encoding='utf-8')
    (target / 'staged.txt').write_text('Fictional staged update\n', encoding='utf-8'); command('add', 'staged.txt')
    (target / 'new item.txt').write_text('Fictional untracked work\n', encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--git-executable', type=Path, required=True)
    args = parser.parse_args()
    try:
        create(args.destination, args.git_executable)
        print(json.dumps({'status': 'FICTIONAL_REPOSITORY_CREATED', 'expected_entries': 3}))
    except (r.ReportError, OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'DEMO_CREATION_FAILED'})); raise SystemExit(2)
