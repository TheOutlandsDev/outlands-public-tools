#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if [ -n "${RESOURCE_MONITOR_PYTHON:-}" ]; then
  exec "$RESOURCE_MONITOR_PYTHON" -B launch.py "$@"
fi
for candidate in python3 python3.15 python3.14 python3.13 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] not in ((3,12),(3,13),(3,14),(3,15)))' 2>/dev/null; then
    exec "$candidate" -B launch.py "$@"
  fi
done
echo 'Install Python 3.12 through 3.15 from https://www.python.org/downloads/ and reopen this terminal. See START-HERE.md.' >&2
exit 2
