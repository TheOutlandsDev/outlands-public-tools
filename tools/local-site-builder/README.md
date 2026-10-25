# Outlands Local Site Builder

A local browser-based block editor for small websites. Create pages from
templates, edit text directly, style sections, upload images, save drafts, and
publish when ready. Original application code is [MIT licensed](LICENSE).

The starter is **Cedar Workshop**, an entirely fictional three-page site. No
family/business content, real uploads, database, credentials or generated private
site is included. The original private website remains separate.

## Start here

For a disposable walkthrough, first define an absolute `$privateWork` outside
the entire checkout using the [private workspace guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/PRIVATE-WORKSPACE.md).
Select an external runtime data root before setup/start:

```powershell
$env:SITE_DATA_DIR = Join-Path $privateWork "site-data"
```

```sh
export SITE_DATA_DIR="$privateWork/site-data"
```

The private, ignored `.env` is still intentionally created beside `server.js`.
Keep it private; the data-root setting does not relocate credentials.

1. Install **Node.js 24 LTS** with npm from [the official Node website](https://nodejs.org/).
   This release deliberately supports Node 24 on Windows and Linux. Native
   `better-sqlite3` installation may need an upstream prebuilt binary or local
   compiler toolchain; no runtime or compiled dependency is included here.
2. Download this repository's source ZIP or clone it. Open a terminal in this
   folder. Confirm `node --version` starts with `v24`.
3. Run:

   ```text
   npm ci
   npm run setup
   npm start
   ```

   On PowerShell, use `npm.cmd` if script execution policy blocks `npm.ps1`.
   Setup asks for a hidden password of at least 14 characters, at most 72 UTF-8
   bytes. It creates a **new** private `.env`; it never overwrites one. Do not put
   a real password in a command argument or an issue report. Automated private
   setup can supply one line through standard input with
   `node scripts/setup.js --stdin`.
4. Open the printed `http://127.0.0.1:3000/admin` URL. Username: **admin**.
   Use your newly chosen password. The public preview is `/` on the same server.
5. Stop with **Ctrl+C** and wait for Node to exit before backup, export or restore.

The editor binds only to `127.0.0.1`. It rejects a different `HOST`, foreign Host
headers, foreign non-opaque browser origins, and changes without a session-bound
CSRF token. This is a local editing tool, not a public CMS server. Browser
webviews that send an opaque `Origin: null` still need the valid session token.
Use one hostname consistently; switching between localhost and 127.0.0.1 changes
the browser cookie origin.

## Editing workflow

1. Select **Welcome**, **Projects** or **About** in the left sidebar.
2. Click text in the center preview, or use the right-side fields. Section design
   controls include colors, heading/body sizes, padding, spacing and corners.
3. Add Hero, Text, Image + Text, Three Cards, Checklist, FAQ, Affiliate Product,
   Call to Action, Divider or Contact blocks. Move, copy or delete individual
   blocks. The editor is intended for a desktop-width browser.
4. **Save Draft** keeps changes private. The editor also attempts draft autosave
   after roughly a minute of unsaved changes. Save explicitly before leaving.
5. **Publish** updates the local public page and generated HTML. Existing public
   content keeps its published text, title and description until republished.
   Publish is **local**; it does not deploy anything to the internet.
6. Use **View Site** or **Open** to check the current published version. Draft
   changes are not a separate public preview URL.
7. Use a page template or **New** for another page. Slugs use lowercase letters,
   digits and hyphens; reserved server paths and duplicate slugs are rejected.
   Save the **Site Menu** separately to control labels, order and visibility.

Deleting a page removes that page's drafts and local generated HTML. The home
page is protected. Deleting an asset removes its source image; references can
then break. Back up before intentional deletions. There is no undo history.

## Images and branding

Upload JPEG, PNG, GIF or WebP images from the Assets panel; select an image block
and insert the uploaded asset. Limit: **5 MiB per image**, 1,000 assets. Uploaded
filenames are replaced with random names. MIME and leading file signatures must
agree; SVG/HTML uploads are rejected. Signature checks do not fully decode an
image, remove metadata, scan for malware or prove ownership. Use images you may
share, and remove sensitive EXIF data separately when necessary.

Change the fictional identity in `content/brand.js` and replace `assets/logo.svg`
with your own appropriate asset. This built-in SVG is trusted source, not an
upload. Edit `content/starter-pages.js` to change **new** site/template defaults;
existing saved pages are not automatically replaced. Restart after code changes.
Changing branding does not republish existing page documents automatically;
publish the pages again or save Site Menu to regenerate published documents.

The editor accepts HTTP(S) image URLs and HTTP(S)/mailto links. Visitors' browsers
can contact those domains. Entering an external image is an intentional network
reference; the app does not download or archive that image for you.

## Where data lives

Private `.env` settings live beside `server.js`. By default, runtime state is
under the ignored `data/` folder:

| Location | Contents |
| --- | --- |
| `data/db/site.sqlite` | Drafts, published pages, menu, asset records, inbox and app logs |
| `data/uploads/images/` | Original uploaded raster files |
| `data/site/` | Generated page HTML and the built-in logo |
| `data/logs/` | Local operational/request logs |
| `data/.owner-lock` | Exclusive editor/maintenance ownership marker |

Use trusted local storage. Symlink/junction ancestors are rejected on checked
paths, but this is not protection against hostile concurrent filesystem changes.
Do not select cloud-synced or network storage for a live SQLite database.

To use a **separate new/restored** data folder:

```powershell
$env:SITE_DATA_DIR = 'D:\MySites\workshop-data'
npm.cmd start
```

```sh
SITE_DATA_DIR="$HOME/my-sites/workshop-data" npm start
```

Do not point this app at the private family site's original database or folders.
There is no supported migration from that unrelated private schema. A data root
must not be shared by two app instances. If a crash/forced termination leaves
`.owner-lock`, stop and verify the owning process is gone before manually
removing **that marker only**. Never remove a lock to bypass an active editor.

## Backup, verify and recover

Backups are **offline**: stop the editor cleanly first. Every output directory
must be new, outside its input root, with an existing parent. Paths below are
examples; select your own private storage.

```text
npm run backup -- "$privateWork/workshop-backup-001"
npm run verify-backup -- "$privateWork/workshop-backup-001"
npm run restore -- "$privateWork/workshop-backup-001" "$privateWork/workshop-restored-data"
```

Backup captures the stopped site's database, uploads, generated HTML and logs.
It records a SHA-256 manifest, checks exact selected members/bytes and SQLite
integrity, and excludes `.env` and the ownership marker. A remaining nonempty WAL
journal is rejected: reopen the editor and stop it cleanly to checkpoint first.
The exclusively created snapshot is switched to SQLite's DELETE journal mode.

Restore verifies checksums and database integrity, then copies to a **new** data
directory. It never merges into or overwrites an existing site. Set
`SITE_DATA_DIR` to the restored folder and start this app using your existing
private `.env`, or run setup separately in a fresh app checkout. Test the public
pages, drafts, inbox and images before relying on a backup.

Limits: 5,000 files, 512 MiB total selected bytes, 64 MiB per member, 240 characters
per portable relative path, 2 MiB manifest. Larger sites need a separately
reviewed backup method. These are corruption checks, not signed authenticity,
encryption, remote backup or atomic crash-proof recovery. An I/O error may leave
partial **new** output for inspection. No automatic cleanup/deletion is attempted.

**Backups are private.** They include drafts, messages, original image metadata
and local logs. Keep credentials separately in an appropriate private store.
Neither backups nor `.env` belong in a public repository.

## Export a public static site

Stop the editor, then:

```text
npm run export -- "$privateWork/workshop-static-001"
```

The new directory contains published HTML as `index.html` and
`slug/index.html`, the original logo and referenced locally uploaded images.
Unpublished pages/drafts, admin code, SQLite, logs, inbox and `.env` are excluded.
Serve the result at a web host's **domain root** with directory-index support;
root-relative links are not designed for a project subpath or double-clicked
`file://` pages. Deployment is a separate user action.

Contact forms require a backend, so static export replaces their forms with an
explanatory message; the displayed email link remains. External images are
references, not copied assets. Review every published page and image for privacy
and rights before uploading the static directory. No automatic deployment exists.

## Inbox and optional email

Contact blocks save messages in the local SQLite inbox. No email is sent by
default. A loopback-only site cannot accept remote visitors' form submissions.
Static exports have no working inbox API.

If you explicitly want to send email from local testing, add private SMTP values
to `.env`, set `EMAIL_SERVICE_ENABLED=true`, and configure `COMMUNITY_EMAIL`,
`OWNER_EMAIL`, `CONTACT_TO_EMAIL`, optional `CONTACT_CC_EMAIL`, `SMTP_HOST`,
`SMTP_PORT`, `SMTP_SECURE`, `SMTP_USER`, `SMTP_PASS` and `SMTP_FROM` as your
provider requires. The built-in example.invalid addresses cannot deliver mail.
SMTP uses finite connection/greeting/socket timeouts. Delivery to a real provider
has not been qualified for this release; the tested default leaves messages local.

The editor uses memory-only sessions: restarting signs users out. Login is limited
to 10 attempts per 15 minutes and contacts to 10 per minute per process. These
single-local-user limits are not public-service abuse protection. Logs/inbox and
assets can contain personal data; do not publish them or expose this server.

## Tests, troubleshooting and contributions

```text
npm ci
npm test
npm run source-check
npm audit
```

The test suite generates its own disposable sites and performs real local HTTP,
SQLite, uploads, draft/publish, CSRF, export and recovery operations. It does not
touch your existing website. See [validation](docs/VALIDATION.md),
[provenance and licenses](docs/PROVENANCE.md), and the
[step-by-step example](examples/WORKSHOP.md).

- **Missing native binding:** use Node 24 and reinstall through `npm ci`. Consult
  [better-sqlite3's installation notes](https://github.com/WiseLibs/better-sqlite3).
- **Port in use:** stop your own earlier instance or choose another `PORT` in your
  private `.env`. Do not terminate unrelated services.
- **403 during an API call:** use the same host, its session cookie and a token
  returned by `GET /api/csrf` in `X-CSRF-Token`. Tokens change after login.
- **Draft is not visible publicly:** select Publish when ready. Save Draft alone
  intentionally keeps the public version unchanged.
- **Backup/export refused:** stop cleanly, check the lock/WAL guidance and choose
  a new output path within the documented size limits.

[Suggestions](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=site_builder_suggestion.yml),
[bug reports](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=site_builder_bug.yml)
and contributions are welcome. Explain the problem and a small fictional
reproduction; code is not required to leave a suggestion. Read
[CONTRIBUTING](CONTRIBUTING.md) and [SECURITY](SECURITY.md) first.

## Collection home

This application is now included in [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/local-site-builder). Download or clone the collection, then open a terminal in `tools/local-site-builder`. The earlier standalone repository remains available as release history. Use the collection issue forms for new bugs and suggestions. Original license and dependency notices are retained.
