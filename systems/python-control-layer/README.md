# Python Data & Query Control Layer 0.1.0

A local health-service foundation, published from the existing first-party
application. All four original application modules and both original test files
retain their exact bytes. It serves two health endpoints and loads configuration;
database connections, data ingestion and query execution are not implemented.

Supported release profiles: **Windows x64 and Ubuntu x86-64, Python 3.12.16**;
the supplied Linux container is separately tested on Ubuntu with Docker Compose.
The original Python 3.12 support range is retained. This is a source release:
obtain Python or Docker and the separately licensed dependencies yourself.

Start with [SETUP.md](SETUP.md). The source ZIP, SHA256SUMS.txt, setup guide,
build manifest and actual validation records are published together. Verify the
ZIP checksum before extracting it. Existing toolkit/wheel bundles are separate.

## Current behavior

| Request | Result |
| --- | --- |
| `GET /health/live` | HTTP 200, `{"status":"alive"}` |
| `GET /health/ready` | HTTP 200, `{"status":"ready"}` |
| Unknown path | HTTP 404 |
| `POST /health/ready` | HTTP 405 |

Readiness means this milestone's service started; it does **not** check a
database, credentials, filesystem availability, connectivity or query readiness.
Settings such as CONTROL_DB_URL and the data-root strings are unused declarations
at this stage. The service does not create or read the configured data directories.

FastAPI supplies OpenAPI/docs routes in addition to those health operations.
No browser workflow or remote docs assets are qualified. Native examples bind
127.0.0.1; Compose publishes its container port on 127.0.0.1 only. The container
listens on all interfaces internally. Keep this unauthenticated foundation local.
Authentication, TLS, internet exposure and production operation are outside scope.

Configuration comes from environment variables and an optional local `.env` in
the working directory. Environment variables take precedence. Unknown dotenv
fields are ignored. Settings are cached; restart the process after changes.
APP_VERSION used for OpenAPI is read at import time. A changed label is a caller
declaration, not proof of different source or a running database.

Startup configures the process root logger, replacing its handlers, and emits
JSON startup/shutdown messages. The formatter includes timestamp, level, logger,
message and an exception string when present. Arbitrary `extra` fields, including
the supplied startup app_version extra, are not emitted. Logs can contain private
messages or tracebacks; do not publish operational logs without separate review.

## Release review

- [BASELINE.json](BASELINE.json) pins the six unchanged original Python files.
- [Qualification](docs/QUALIFICATION.md) defines installed-source, live HTTP and
  separate Linux container checks. Two original tests plus 14 new checks are used.
- [Origins](docs/ORIGINS.md) explains retained implementation and packaging changes.
- [Dependency review](DEPENDENCY-REVIEW.json) records a known-advisory lookup for
  31 locked versions, including conditional-platform dependencies. This is not
  a security certification or a promise about future advisories.
- [Dependency metadata](DEPENDENCIES.json) and [notices](THIRD-PARTY-NOTICES.md)
  identify separately obtained packages and licenses.

The test stack retains one visible StarletteDeprecationWarning: its HTTPX
compatibility path recommends httpx2. The preserved tests currently pass with
the pinned HTTPX compatibility dependency; the warning is recorded, not filtered.

No actual database, dataset, operational dotenv, private log, interpreter,
dependency wheel or container image is bundled. Original runtime storage and
unrelated source families are outside this selected publication.
