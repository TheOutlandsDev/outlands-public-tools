# Provenance and dependency boundaries

This is an original-owner-authorized MIT adaptation of a private local website
builder. The selected editor HTML/CSS/JavaScript, renderer and server were
reviewed as personally authored, assistant-assisted application source. No
separate third-party implementation/required source notice was identified in
those selected files. Owner authorization is the authorship basis, not a claim
of independently proven exclusive authorship.

The public work retains the generic block-editor interface and rendering
mechanisms, replaces the business-specific identity/templates, and adds original
validation, security boundaries, setup, offline recovery/export, synthetic tests
and documentation. The original site and its selected source files remain
unchanged. Original databases, credentials, uploads, branded/generated images,
published pages, logs, backups and unrelated scripts are excluded. The fictional
templates and simple SVG logo are original source created for this release.

[MIT](../LICENSE) applies to the original application source, tests, examples and
documentation. It does not grant rights in a user's future content, Node.js,
SQLite, browsers, npm packages or their compiled dependencies.

## Pinned dependencies

| Direct package | Pin | Declared upstream license |
| --- | --- | --- |
| express | 5.3.0 | MIT |
| express-session | 1.19.0 | MIT |
| multer | 2.5.0 | MIT |
| better-sqlite3 | 13.0.3 | MIT |
| bcryptjs | 3.0.3 | BSD-3-Clause |
| dotenv | 18.0.9 | BSD-2-Clause |
| nodemailer | 10.2.1 | MIT-0 |

The resolved installation was inspected against `package-lock.json` rather than
assuming all JavaScript packages share the app's MIT license. The full package
inventory, versions, SPDX expressions, source repository metadata and integrity
pins are recorded in [DEPENDENCIES.json](DEPENDENCIES.json). Retained license
texts are in [THIRD-PARTY-NOTICES.txt](../THIRD-PARTY-NOTICES.txt). No node_modules,
native SQLite binding, compiler, browser or Node runtime is shipped in this source
repository. npm installs dependencies separately with their own notices/terms.
SQLite and the native toolchain may have additional upstream notices; consult the
installed package when redistributing a bundled application.

`npm audit` reported no known advisories for this exact dependency graph on
2026-10-25. This is a dated database check, not proof that dependencies have no
vulnerabilities. Recheck before later releases; do not blindly update the lock
without tests and notice review.

Primary references consulted for implementation constraints:

- [Express security guidance](https://expressjs.com/advanced/best-practice-security/)
- [express-session, including MemoryStore limitations](https://github.com/expressjs/session)
- [better-sqlite3 API and backup documentation](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/api.md)
- [SQLite backup and consistency notes](https://www.sqlite.org/backup.html)

The release uses a stopped/checkpointed database for offline backup. It does not
claim whole-site live transaction consistency, safe remote administration or a
production-ready public session store. It adds no official association with the
dependency authors or any service provider.
