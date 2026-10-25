# Fictional walkthrough

`make_demo.py` creates an invented JSON project matching the documented
structural subset, a hash-bound mapping, and one or two empty placeholder files.
It neither reads real media nor starts an editor. The fixture is not claimed to
be an editor-compatible project. Choose a new absolute destination under an
existing private parent outside the checkout; set `$privateWork` accordingly in
PowerShell. Use equivalent absolute paths on Linux.

## Inventory without following anything

```powershell
python -B examples/make_demo.py --destination "$privateWork/vpd-missing-demo"
python -B vpd_references.py --project "$privateWork/vpd-missing-demo/project.vpd" --output "$privateWork/vpd-only-report"
```

Expected: exit 0, `INVENTORY_ONLY`, three reference rows and zero metadata checks.
The project-record path is `ref-000001`; two invented video-bin paths are
`ref-000002` and `ref-000003`. None of their embedded absolute strings is followed.
Report text omits those strings by default. IDs in your own project can differ.

## Demonstrate a missing mapped copy

```powershell
python -B vpd_references.py --project "$privateWork/vpd-missing-demo/project.vpd" --mapping "$privateWork/vpd-missing-demo/mapping.json" --media-root "$privateWork/vpd-missing-demo/copies" --output "$privateWork/vpd-missing-report"
```

Expected: exit **1**, `REVIEW_REQUIRED`. One regular placeholder is present and
one selected mapped path is missing. This nonzero finding result is intentional.
The report directory still contains a completed report set. A failed parse/I/O
run instead returns exit 2 and claims no completed set.

## Demonstrate a metadata-only no-findings result

```powershell
python -B examples/make_demo.py --destination "$privateWork/vpd-present-demo" --complete
python -B vpd_references.py --project "$privateWork/vpd-present-demo/project.vpd" --mapping "$privateWork/vpd-present-demo/mapping.json" --media-root "$privateWork/vpd-present-demo/copies" --output "$privateWork/vpd-present-report"
```

Expected: exit 0, `NO_MAPPING_FINDINGS`, two attempted mapped checks with regular
file observations. Both files are empty: that result deliberately demonstrates
that existence does not establish playable media, correct correspondence or
successful migration. No file body is read or hashed by the checker.

Open the report HTML locally, or independently verify the manifest from Python:

```python
import hashlib, json
from pathlib import Path
report = Path(ABSOLUTE_PRIVATE_REPORT_DIRECTORY)
manifest = json.loads((report / "MANIFEST.json").read_text(encoding="utf-8"))
assert {row["path"] for row in manifest["files"]} == {"report.json", "report.html"}
for row in manifest["files"]:
    data = (report / row["path"]).read_bytes()
    assert len(data) == row["bytes"]
    assert hashlib.sha256(data).hexdigest() == row["sha256"]
```

Replace `ABSOLUTE_PRIVATE_REPORT_DIRECTORY` with a quoted absolute path. Review
all paths in an untrusted manifest before using it outside this generated
example. These checks show report-byte agreement, not authenticity or media
integrity. Do not publish generated reports or actual project/mapping data by
default. Read [the full format contract](../docs/FORMAT.md).
