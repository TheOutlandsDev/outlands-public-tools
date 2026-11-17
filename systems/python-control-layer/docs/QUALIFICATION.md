# Qualification contract

Two native archive lanes use complete hash-pinned CPython 3.12.16 SDKs on Windows
x64 and Ubuntu x86-64. Each extracts a fresh source ZIP, verifies its manifest and
six original-file pins, creates a new venv, installs only binary dependencies from
the hash-locked validation file, builds/installs the local source with the pinned
backend and verifies installed app bytes. Tests import that installed package;
they do not accidentally import the repository copy. `pip check` must pass.

All 16 tests must be selected, started and pass, with no skips/failures/errors.
The two original tests retain bytes. Added checks cover original pins, health-only
OpenAPI operations, 404/405 behavior, settings defaults, environment/dotenv
precedence, cached settings, invalid logging startup, JSON lifecycle logs, escaped
newlines/exceptions, omission of arbitrary log extras, process root logger behavior
and readiness without storage operations. The exact observed HTTPX compatibility
deprecation remains recorded. It is not filtered or called an application failure.

Each native lane separately starts one installed Uvicorn child on an OS-selected
127.0.0.1 port. Actual TCP HTTP checks cover both health routes, unknown routes and
unsupported methods. An owned local control file requests graceful shutdown; no
HTTP shutdown endpoint is added. Exit, lifecycle messages and absence of configured
storage-directory creation are verified. Private raw logs are not public assets.

A separate Ubuntu Docker lane builds the supplied runtime/test stages from the
same extracted archive. It runs all 16 tests, starts the supplied Compose service,
waits for its real healthcheck, checks HTTP, non-root identity, read-only root and
loopback-only host publication, then verifies clean shutdown. Only owned Compose
resources are cleaned up. The immutable base-image index and exact dependency
wheel hashes bind that profile; Docker/Compose versions are recorded.

CI rebuilds the source ZIP independently and compares exact archive/build-manifest
bytes. Native validation records pin SDK preparation, source revision, dependency
versions, original-file hashes, selected/started/successful IDs and HTTP outcomes.
Anonymous acceptance downloads the five release assets without authentication,
verifies checksums/Git/manifest bytes and runs another fresh Windows native install.
It records omitted reference rebuilds honestly.

Dependencies were resolved with uv 0.13.8 for the retained Python 3.12 scope. Both
universal lock files include conditional-platform pins and distribution hashes.
The reviewed advisory lookup covers all 31 exact validation/runtime versions,
including Linux-only uvloop and Windows-only colorama. The reduced public review
binds both locks and reports zero known advisories at review; raw tool output stays
private. This is a bounded advisory lookup, not a complete security assessment.

No database/query, real data, production network, authentication, browser workflow,
Docker Desktop on Windows or business operation is qualified. Readiness is a fixed
milestone-0 service response. The original application is preserved rather than
silently changing that meaning. No full original-family clearance is implied.
