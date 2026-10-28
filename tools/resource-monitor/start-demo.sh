#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
for candidate in python3.13 python3.12 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] not in ((3,12),(3,13)))' 2>/dev/null; then
    exec "$candidate" -B launch.py "$@"
  fi
done
echo 'Install Python 3.12 or 3.13 from https://www.python.org/downloads/ and reopen this terminal. See START-HERE.md.' >&2
exit 2
