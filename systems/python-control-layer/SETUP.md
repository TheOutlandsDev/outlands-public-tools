# Setup and fictional validation

Use a new private directory for the extracted source. Verify the ZIP against
SHA256SUMS.txt first. This source release requires separately installed Python
3.12 (qualified with 3.12.16) or a working Docker/Compose installation. No admin
rights are needed for a native project venv when Python is already available.
These instructions do not install Docker, change policy or alter system services.

## Windows native

From the extracted source directory in ordinary PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.lock
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use the actual Python 3.12 executable instead of `py -3.12` if no launcher is
installed. Activation is unnecessary; execution-policy changes are unnecessary.
Stop the foreground server with Ctrl+C. In another PowerShell window:

```powershell
curl.exe --fail http://127.0.0.1:8000/health/live
curl.exe --fail http://127.0.0.1:8000/health/ready
```

The two JSON bodies are `{"status":"alive"}` and `{"status":"ready"}`.
Neither response verifies a database or data directory. No original data is used.

## Ubuntu native

From the extracted source directory, using your Python 3.12 executable:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.lock
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, run the same two loopback curl requests. Stop with Ctrl+C.
If venv support is unavailable, obtain an approved Python installation before
continuing; this guide does not request system package or policy changes.

## Optional private settings

Review `.env.example` before copying it to `.env`. Its values are generic examples;
it contains no actual account, secret, host or dataset. Real dotenv files remain
private and ignored by Git. Environment values override the working-directory
dotenv file. Restart after changes because configuration is cached. Invalid
LOG_LEVEL prevents startup; unsupported database strings do not prevent readiness
because no database operation exists in milestone 0.

## Tests and installed-package check

Install the complete hash-locked validation set in the venv above:

```text
python -m pip install --require-hashes --only-binary=:all: -r requirements-validation.lock
python -m pip install --no-deps --no-build-isolation .
python -m pip check
python -B -m pytest -q -p no:cacheprovider
```

Here `python` means the venv executable, not a system interpreter. The validation
lock includes the exact build backend needed by --no-build-isolation. Expected:
16 passing tests and one recorded Starlette HTTPX compatibility deprecation.
The first two tests are the unchanged originals. Fourteen added tests cover source
preservation, route scope, invalid requests, settings precedence/cache behavior,
invalid startup configuration, logging schema/lifecycle and declarative readiness.

`packaging/smoke_http.py` adds a real TCP exercise around one owned server child.
It chooses a free loopback port, checks 200/404/405 JSON responses, requests graceful
shutdown through a local owned control file and waits for exit. It adds no
application shutdown route and changes no firewall or service setting. Choose
new external workspace/report paths when invoking it:

```text
python -I -B packaging/smoke_http.py --workspace NEW_EXTERNAL_WORKSPACE --report NEW_EXTERNAL_REPORT.json
```

Replace both placeholders with new absolute paths under an existing private parent.
This helper expects the package installed in that venv, as above. Test artifacts
and raw logs stay outside the source and remain private.

## Linux Docker Compose

From the extracted source directory with an already approved Docker installation:

```text
docker compose build control-api
docker compose up -d --wait control-api
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
docker compose --profile test run --build --rm -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 tests
docker compose down
```

The supplied image reference pins Python 3.12.16-slim-bookworm by OCI index digest.
Runtime dependencies are hash-locked. Runtime and test stages use UID/GID 10001;
Compose makes their root filesystem read-only and provides temporary /tmp.
The runtime stage omits validation-only packages. Compose binds host port 8000
to 127.0.0.1. No source/data/runtime bind mounts are required or supplied for this
health-only milestone. Choose a free local port if 8000 is already occupied and
update the loopback port mapping and requests together. Do not stop unrelated
services or remove other containers to free it.

Ubuntu CI exercises these Compose definitions, actual container health status,
HTTP responses and clean shutdown. Native Windows qualification does not establish
Docker Desktop support on Windows. The Docker daemon, host OS and client versions
are measured dependencies of that profile, not bundled or independently certified.

## What this establishes

The release preserves the selected application and tests and validates installation,
startup/configuration, HTTP health behavior and shutdown with fictional settings.
It does not add a database driver, SQL executor, ingestion pipeline, access control,
authentication, production readiness or business workflow. Review those as separate
future changes. Retain operational settings, data and logs privately.
