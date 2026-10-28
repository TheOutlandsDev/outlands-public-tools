# Shared public catalog and release coverage

`registry.json` is the editable source for component titles, purposes,
requirements, example/validation references and next-package assignments.
`packages/catalog.json` is the explicit frozen release plan. These have different
jobs: a new public application can be listed without pretending it is inside an
older immutable download.

## Keep a new application in the directory

1. Finish the application's source/rights review and normal validation first.
2. Add its registry entry in the same change. Copy a neighboring record or run:

```text
python -B catalog/manage.py scaffold --path systems/NEW-ID --group systems --title "Application title" --purpose "The user's task" --requirements "Actual runtime requirements"
python -B catalog/manage.py generate
python -B catalog/manage.py check
```

For a tool use `tools/NEW-ID` and an existing family ID. Replace the placeholders;
scaffolding requires an actual module README. Review the generated default
README references and replace them with focused examples and validation records.
The check refuses missing, duplicate or obsolete components, wrong families,
missing metadata and nonexistent evidence links. New source outside the released
snapshot is explicitly reported in `pending_packaging` and labeled source-only.
Its family assignment records where it belongs in the next package.

## One generated view for GitHub and the portfolio

`generate` writes three deterministic files under `catalog/generated`: a readable
GitHub index, the portfolio directory fragment and its JSON data. `check` refuses
stale generated output. Existing tool/source code is not rewritten.

After opening the existing Site with the Sites source helper, apply the exact
same generated view to its local source:

```text
python -B catalog/manage.py apply --site EXISTING_PORTFOLIO_CHECKOUT
```

This checks the public release and each download's size/digest before changing
the Site's existing directory and JSON file. It requires the existing hosting
manifest and preserves the rest of the landing page. Use the normal Sites
validation, save and deployment workflow afterward. This command does not grant
access, store credentials or deploy a Site by itself. CI detects registry/output
drift; it does not hold permanent credentials for the separate portfolio host.

## Release a new reviewed snapshot

Keep existing tags/assets unchanged. Update the frozen version and source pin in
`packages/catalog.json`, align its membership with the registered source, and run
the package/workshop tests. The published snapshot is an explicit review choice,
not an automatic inclusion of any directory found on disk.

The packaging workflow tests fresh archives on Windows/Ubuntu, compares all
checksums, then publishes a new named release on main. It refuses to replace an
existing release. The release tag is created by the authenticated CI publisher;
no permanent local access token or private instance is needed.

After the download assets exist:

```text
python -B catalog/manage.py verify-release --tag toolkit-vVERSION
python -B catalog/manage.py activate --tag toolkit-vVERSION
```

Activation verifies the actual public assets, changes the published-release
pointer and regenerates both indexes. Commit that small metadata change, then
apply and publish the portfolio projection. A candidate plan or successful source
test alone never activates a download link. CI runs a public release verification
when the active release pointer changes.

## Workshop evidence

Every family has a [five-minute fictional workshop](../workshops/README.md).
The fresh-archive tests exercise 33 underlying CLI commands across eight
families. These are bounded CLI checks, not acceptance of every tool, GUI,
device, live provider, model or game. Expected and observed results stay separate.


## Focused handoffs around unchanged application source

The two workbench download packages keep the manifest-pinned application directory
unchanged under application/ and add outer START-HERE.md and PROVENANCE.md guides.
Their package version is 0.1.1; the application source still declares 0.1.0.
Only activate a focused_release entry after its published ZIP, release matrix and
checksums match the reviewed candidate. The registry may specify start_guide and
provenance paths outside the application tree; both must resolve inside this repo.
Those paths are linked at the immutable focused-release tag. The demo field links
the original fictional outcomes on the portfolio. Existing app-owned guides retain
their earlier defaults. Toolkit coverage remains a separate frozen source pointer;
a focused release alone never silently changes complete-archive membership.
