# Selected original-source publication

This release selects the owner-authorized first-party health-service application,
not a fresh conceptual replacement. All four original app modules and both
original test files retain exact raw bytes, including line endings. BASELINE.json
provides their SHA-256 pins. Source ownership review relies on the owner's
first-party authorship confirmation and explicit authorization for this selected
sanitized publication; it is not independent legal certification.

The retained implementation loads cached Pydantic settings, configures JSON root
logging and serves fixed liveness/readiness responses through FastAPI. Its two
original tests remain unchanged. Fourteen additional tests are separate.

Packaging changes update and hash-lock separately obtained dependencies, retain
the declared Python 3.12 range, add install/HTTP/container qualification methods,
and pin the Linux base image. The new container copies source before running it,
separates runtime/test dependency sets and uses a non-root user. The supplied
Compose file removes unused original data bind mounts, keeps loopback publishing
and adds a read-only root filesystem with temporary /tmp. Generic settings are
reviewed examples. No actual dotenv, storage, database, dataset, log or third-party
binary is exported. Original packaging snapshots and selection metadata remain
private; original sources are left untouched.

Selected first-party source is provided under this repository's MIT license.
External imported libraries retain their own licenses and are not relicensed by
this release. Their code/images/interpreters are obtained separately. See the
dependency metadata and notices. This selection does not clear unrelated programs,
customer/employer material or original runtime records elsewhere.
