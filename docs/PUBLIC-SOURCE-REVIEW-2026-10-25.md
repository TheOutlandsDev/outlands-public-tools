# Current collection source review

The 2026-10-25 review revisited every pattern finding in the selected collection
source. The owner chose TheOutlandsDev as the copyright identity for the two
imported applications that previously included a personal owner attribution.
Their MIT grants are unchanged, their exact source manifests were refreshed,
and third-party notices were preserved byte-for-byte.

The initial scan contained 96 findings. The two owner-attribution matches were
corrected. A concurrent addition of Offline ELF Inspector contributed one
fictional Windows CLI-path example. All 95 findings in the combined current
tree have an explicit disposition bound to the reviewed file's SHA-256 in the
private review record:

| Disposition | Findings | What was reviewed |
| --- | ---: | --- |
| Required third-party attribution | 62 | 61 upstream license/contact lines and one retained copyright URL with Markdown punctuation |
| Pattern false positive or fictional example | 31 | Programming attributes, slices, Windows stream names, example paths, loopback URL interpolation, URL rejection cases, regular-expression escapes, and a disposable test password |
| Public text configuration | 1 | npm boolean policy settings without credentials, registry addresses, account names, environment expansion, or local paths |
| Original vector asset | 1 | The release-created SVG logo, with no script, event handler, external image/link, or metadata |

There are zero unresolved findings in this selected-tree pattern review. The
automated auditor still returns `REVIEW_REQUIRED`; no detector was disabled or
globally allowlisted to obtain a clean result. Required upstream author names
and contact addresses remain in third-party legal notices. These are retained
attributions, not application user records or connection configuration.

## Scope

This is a review of the current selected source and fictional examples. It does
not establish exclusive intellectual-property ownership, catch every possible
secret, or clear the drive's unselected projects. Application stores, player or
customer records, credentials, operational configurations, generated reports,
backups, game/plugin assets, and dependency implementations remain excluded.

The copyright correction applies to the current files and new curated source
packages. Earlier Git commits and the original standalone repositories may
retain prior owner attribution. Repository history was not rewritten. Private
marker lists, finding reports, source mappings, and evidence ledgers remain
outside this public repository.

Use [Public Release Audit](../tools/public-release-audit/README.md) on any new
export and review its findings against its exact bytes. Passing checks or
retaining these dispositions does not approve a future changed file or an
operator's input data.
