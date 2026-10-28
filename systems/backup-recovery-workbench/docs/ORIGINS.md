# Source and design origins

This standalone first-party MIT implementation adapts the owner's generic archive
method: explicitly approved source sets, source/destination inventory comparison,
failure classification and per-set completion records. The original archive helper
was inspected as source only; its copy commands, schedule, tests and operating
configuration were not run or changed.

The new application replaces host-specific copy commands with bounded guarded
Python I/O, per-file hashes, source-change checks, exact tree verification, exclusive
completion markers, typed append-only jobs, fresh restore drills and conservative
retention. It adds an independent-pinned recovery path for a fresh instance with
no original index, plus a CLI/browser UI and reviewed private metadata reports.

No original source-set paths, target mappings, schedules, host details, logs,
backups, customer/user records, configuration, credentials or third-party/game assets
are included. All public input specifications, file contents, labels and actors are
newly invented. The broader original application family remains separately held.

`recovery/vendor/` contains unchanged public first-party native file/store I/O
helpers from Reliability & Incident Workbench. The private-instance runtime changes
only its format/schema/directories and fictional-input seeding. HTTP, packaging,
test and documentation patterns adapt the existing public workbenches. Optional
hash-pinned browser dependencies are reused unchanged and are not bundled.

First-party source is MIT, copyright TheOutlandsDev. Python/SQLite/native APIs and
separately installed browser tooling retain their own terms. Future caller inputs,
backup payloads and reports retain their rights and privacy requirements; this
source release grants no rights to redistribute them.
