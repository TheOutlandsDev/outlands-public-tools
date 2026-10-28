# Downloadable OUTLANDS Toolkit

[Download Toolkit 0.2.1](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/toolkit-v0.2.1)
for the complete source collection or one of eight tool families.

This release pins public source revision
`758186925e22ad70402f61218a7c3ecdfe078ba9`: 62 tools, seven systems and the shared
methodology. Newer work can continue on main without silently changing a download.
The source files retain their exact Git bytes. Packaging code and three worked
methodology examples have a separate recorded packaging revision.

| Package | Included primary components |
| --- | --- |
| Complete | All 62 tools and all seven systems |
| Release and developer QA | 15 tools |
| File, backup and workflow | 9 tools |
| Document and media inspection | 6 tools |
| Android and Linux inspection | 13 tools |
| Desktop diagnostics | 7 tools |
| Local productivity applications | 4 tools |
| Data and AI tools | 6 tools |
| Game utilities | 2 tools; source and fictional fixtures, no game payloads |

All archives include shared methodology, legal notices and collection documents.
Family archives preserve original paths; related cross-family documentation may
need the complete archive or the pinned online collection. Six systems are in
the complete archive; the six larger workbenches also retain their earlier
focused application releases. Workfloor and Code Atlas retain separate releases.

## Download and verify

1. Download your ZIP and `SHA256SUMS.txt` from the same named release.
2. Compare its SHA-256 against the listed filename before extracting.
3. Extract into a new directory and read `START-HERE.md`.
4. Follow the selected module's runtime and platform guide. No runtimes,
   installed dependencies, native drivers, model weights or game files are bundled.

PowerShell: `Get-FileHash -Algorithm SHA256 ./outlands-complete-0.2.1.zip`.
On Linux, `sha256sum --check --ignore-missing SHA256SUMS.txt` checks present assets;
ensure the chosen ZIP is explicitly reported OK. Checksums from a single source
prove consistency, not authenticity. Keep the checksum from a trusted view.

Every archive contains `PACKAGE-MANIFEST.json` with each member's size/hash and
the exact source and packaging revisions. The manifest excludes itself; the
external ZIP checksum covers it. Catalog and release-matrix JSON provide all
download links, counts and hashes. No generated private audit log is included.

## Try the methodology

Use the complete or release-QA archive to run
[three fictional examples](../methodology/worked-examples/README.md). They cover
source inventory changes, lock comparison and a missing-document failure/fix.
The example runner writes a new private scratch directory, installs nothing and
refuses existing destinations. Other families retain per-tool fictional examples.

## Rebuild from the packaging revision

Clone the public repository with Git history, check out the packaging revision
from the manifest, then run with Python 3.12/3.13:

```text
python -B -m unittest discover -s packages/tests -v
python -B packages/build.py --output NEW_EXTERNAL_OUTPUT_DIRECTORY
```

The output parent must exist; the destination must be new and outside the checkout.
Git supplies the exact public source objects; untracked files and local runtime
state never enter a package. ZIP ordering, timestamps and permissions are fixed.
Stored ZIP members avoid compression-library version differences.

## Verification limits

Packaging checks cover coverage, exact bytes, deterministic archives, manifest
tamper/missing/extra rejection and fresh-extraction fictional workflows on Windows
and Ubuntu. They do not rerun every app's native, GUI, device or service tests.
Each preserved module README/validation record remains authoritative. Fixture
success does not establish production suitability, universal privacy or rights
in future user inputs. Original code was developed with AI assistance.

## Shared catalog and family workshops

The [shared registry](../catalog/README.md) generates the GitHub and portfolio indexes and flags new source missing metadata or packaging. Each family now includes [one five-minute workshop](../workshops/README.md); fresh-extraction checks run all eight workshops and their 33 CLI commands on Windows/Ubuntu. Existing 0.2.0 downloads remain unchanged.
