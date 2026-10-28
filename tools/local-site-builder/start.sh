#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo 'Install Node.js 24 LTS with npm from https://nodejs.org/ and reopen this terminal. See START-HERE.md.' >&2
  exit 2
fi
if [ "${1-}" = '--check' ]; then exec node scripts/doctor.js --check; fi
exec node scripts/doctor.js --start
