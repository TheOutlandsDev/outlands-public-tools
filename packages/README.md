# Downloadable OUTLANDS Toolkit

[Download Toolkit 0.5.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/toolkit-v0.5.0).
Frozen public source `9a1b5641444888e87dd43ec8d1adfd0faf712d71` contains 62 tools,
15 systems and shared methodology. Application bytes stay exact; packaging and
worked exercises carry a separate recorded revision.

| Package | Included primary components |
| --- | --- |
| Complete | All 62 tools and 15 systems |
| Release and developer QA | 15 tools |
| File, backup and workflow | 9 tools |
| Document and media inspection | 6 tools |
| Android and Linux inspection | 13 tools |
| Desktop diagnostics | 7 tools |
| Local productivity applications | 4 tools |
| Data and AI tools | 6 tools |
| Game utilities | 2 tools; source and fictional fixtures only |

Systems are in the complete ZIP. All families carry shared methodology, legal
notices, workshops and collection documents. Cross-family guides may require the
full tree or pinned online source. [Windows runtime bundles](../docs/START-HERE.md)
remain separate. These source ZIPs include no installed runtimes or dependencies.

## Download and verify

1. Download the chosen ZIP and SHA256SUMS.txt from the same release.
2. Compare its SHA-256 with the exact listed filename before extraction.
3. Extract into a new directory and read START-HERE.md.
4. Supply the chosen module's runtime/dependencies according to its own guide.

PowerShell: `Get-FileHash -Algorithm SHA256 ./outlands-complete-0.5.0.zip`.
Linux: `sha256sum --check --ignore-missing SHA256SUMS.txt`; confirm the chosen ZIP
is explicitly reported OK. Checksums show consistency, not publisher identity.
PACKAGE-MANIFEST.json records member sizes/hashes and both pins; the external ZIP
hash covers the manifest. catalog.json/release-matrix.json record URLs and digests.

## Two new system exercises

Use the complete ZIP, Python 3.12/3.13, and a new absolute scratch directory whose
parent exists outside the package:

```text
python -B workshops/system_exercises.py --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

Expect two exercises and 33 CLI command checks:

- [Reviewed import](../workshops/import-migration.md): seven invented rows, three
  records, five provenance entries, two rejections. Missing rejection approval,
  repeats and conflicting keys are refused. Direct read-only SQLite checks verify
  actual values and preservation of the existing store and input bytes.
- [Pinned documents](../workshops/document-template.md): two revisions/previews/DOCX
  files, two item rows and total seven. Independent ZIP/XML checks verify wording,
  sections and values. An unreviewed build is refused and old output is preserved.
  Review generated pages in the intended viewer before use.

The runner refuses existing paths. Instances, stores, documents, reports and backups
remain private. Original methodology examples and eight family workshops are also
included; see [workshops](../workshops/README.md).

## Rebuild and qualification

From a committed checkout, use new external output directories:

```text
python -B -m unittest discover -s packages/tests -v
python -B packages/build.py --output NEW_EXTERNAL_PACKAGE_DIRECTORY
python -B packages/release_check.py --output NEW_EXTERNAL_PACKAGE_DIRECTORY
```

The 19 tests check 77-component coverage, original bytes, inventories, refusal,
determinism, fresh extraction, three methodology examples, eight family workshops,
six CLI demos and both system exercises. Windows/Ubuntu must produce matching ZIPs.
Separate fresh complete-ZIP qualification runs both exercises and all 40 Chromium
workflows per platform. Ubuntu renders both exact exercise documents using separately
installed LibreOffice/Poppler; visual review is recorded separately. This does not
certify every live device, GUI, service, Word layout or production workflow.
See [review](REVIEW.md) and [release notes](RELEASE.md).

Toolkit 0.4.0, earlier downloads and Windows bundles remain unchanged. Future source
stays pending until separately packaged. The release manifest/catalog defines the
archive even when preserved repository docs or online indexes describe other revisions.
