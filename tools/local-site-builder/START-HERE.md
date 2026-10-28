# Download to a first website

**Local Site Builder 1.0.2 · Node.js 24 LTS with npm · Windows / Linux.**
This source ZIP needs dependencies installed separately. It is a single-user
local editor; publishing changes only the local preview. No internet hosting,
real website, credentials, database or runtime is included.

1. Download the ZIP and `SHA256SUMS.txt` from the same release. Compare the ZIP
   SHA-256 using PowerShell `Get-FileHash ZIP_PATH -Algorithm SHA256` or Linux
   `sha256sum ZIP_PATH`. Extract into a **new local folder**, not over an old app.
2. Open a terminal in the extracted app folder (the one containing this file).
   Install Node.js **24 LTS with npm** from <https://nodejs.org/> if needed.
   `node --version` must begin with `v24`.
3. Run `npm ci` (`npm.cmd ci` on PowerShell). This downloads the locked
   dependencies. SQLite uses a native binding: if no upstream binary is available,
   a local compiler and SDK may be required. See the official
   [better-sqlite3 installation guide](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/troubleshooting.md).
   The launcher never installs software or changes execution policy.
4. Run `npm run setup` (`npm.cmd run setup` on PowerShell). Choose a new local
   password when prompted; input is hidden. Keep the generated `.env` private.
5. **Once**, select a new private data directory outside the app by appending
   a line to `.env`. Example, with your own actual absolute local path:

   ```text
   SITE_DATA_DIR="/home/YOUR_ACCOUNT/cedar-workshop-data"
   ```

   On Windows use an absolute path with forward slashes, for example
   `SITE_DATA_DIR="D:/PrivateSites/cedar-workshop-data"`. Choose a trusted local
   drive and existing parent. Environment `SITE_DATA_DIR` takes precedence.
   Keep the **same path** on later launches. This is where your site persists.
6. Run `start.cmd --check` on Windows or `sh start.sh --check` on Linux.
   Checks print actionable failures, without printing settings or creating data.
   Then run `start.cmd` or `sh start.sh`. Open the printed loopback `/admin` URL,
   username **admin**, and use your new password.

Use the fictional Cedar Workshop starter. Edit a headline, **Save Draft**, then
open the public preview: it keeps the old text. **Publish** explicitly and reload
the public preview to see the new text. Stop with Ctrl+C and wait for exit;
restart with the same launcher/data path and log in again. Your site remains,
while sessions intentionally expire on restart.

## Recover a stopped site

Choose new absolute backup and restore paths with existing parents. From this
app folder, after stopping cleanly:

```text
npm run backup -- ABSOLUTE_NEW_BACKUP_DIRECTORY
npm run verify-backup -- ABSOLUTE_BACKUP_DIRECTORY
npm run restore -- ABSOLUTE_BACKUP_DIRECTORY ABSOLUTE_NEW_RESTORED_DIRECTORY
```

Use `npm.cmd` on PowerShell if needed. Set `SITE_DATA_DIR` in your private `.env`
to the new restored directory, restart and compare the published page and newer
private draft. Existing restore destinations and corrupt backups are refused.
Backups include private drafts, uploads and logs; they exclude credentials.
Keep both backups and `.env` private. No automatic overwrite, migration or cleanup.

If startup is refused, run the check command. For an occupied port select a free
`PORT` in `.env`; do not terminate unrelated programs. If `.owner-lock` remains
after a crash, follow [the lock guidance](README.md#where-data-lives), never remove
an active editor's lock. See [the verified ZIP workflow](docs/DOWNLOAD-CHECK.md),
[full requirements and limits](README.md), and [design methodology](docs/PROVENANCE.md).
