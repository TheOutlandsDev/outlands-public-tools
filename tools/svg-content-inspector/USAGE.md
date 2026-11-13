# Fictional static SVG inspection walkthrough

Extract the [SVG Content & Reference Inspector 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/svg-content-inspector-v0.1.0) and verify SHA256SUMS. Supply ordinary CPython 3.12, 3.13, 3.14 or 3.15 with **actual Expat 2.10.0 or newer**. A Python version or archive name alone does not establish that prerequisite. The source ZIP contains no interpreter, parser library, compiler, artwork or report, and no third-party Python distribution is needed.

Use a maintained approved interpreter/parser build with recorded provenance. Keep the 2.10.0 runtime refusal intact; do not patch the reported version or lower the floor. Qualification records actual executable/pyexpat/parser source and artifact hashes. Some unmodified standalone Python builds still contain Expat 2.9.0 and correctly fail this release. The floor is not a certificate that every parser vulnerability is fixed or that SVG is safe to render.

Choose an existing trusted private parent outside the source checkout and public/synchronized folders. Substitute your actual approved interpreter, source and private parent for the fictional paths below. Choose a new environment path. There is no administrator privilege, activation, account login, package installation or execution-policy change in these commands. Actual tool/build permissions and workplace policies apply.

PowerShell:

```powershell
$source = 'D:\Source\svg-content-inspector-0.1.0'
$approvedPython = 'D:\Tools\updated-python\python.exe'
$privateWork = 'D:\Private\svg-review'
& $approvedPython -I -B -c 'from xml.parsers import expat; print(expat.EXPAT_VERSION); assert expat.version_info >= (2,10,0)'
& $approvedPython -I -B -m venv --without-pip (Join-Path $privateWork 'new-environment')
$py = Join-Path $privateWork 'new-environment\Scripts\python.exe'
& $py -I -B (Join-Path $source 'svg_inspector.py') --help
```

Ubuntu:

```sh
source=/path/to/svg-content-inspector-0.1.0
approved_python=/path/to/updated-python/bin/python3
private_work=/path/to/private-svg-review
"$approved_python" -I -B -c 'from xml.parsers import expat; print(expat.EXPAT_VERSION); assert expat.version_info >= (2,10,0)'
"$approved_python" -I -B -m venv --without-pip "$private_work/new-environment"
py="$private_work/new-environment/bin/python"
"$py" -I -B "$source/svg_inspector.py" --help
```

## Run all eleven cases unchanged

Save the single Python block below as `fictional_walkthrough.py` in your private parent. Run it with assertions enabled. It refuses an older actual parser before creating its workspace, invokes the raw fictional generator and writes three additional tiny authored text inputs. Six fixture files are retained unchanged. It never reads actual artwork, renders SVG, launches a browser or opens a reference as a file/media/network resource.

The clean case returns exit 0. Review, private-details and static escaping cases return the expected exit 1: they are completed inspections requiring review. Six refusal cases return exit 2. Together with successful fixture generation, there are two exit-0, three exit-1 and six exit-2 outcomes. Every complete JSON stdout object, empty stderr and native line ending is checked.

Four completed reports each contain report.json, static report.html and MANIFEST.json. The script reads complete reports, independently checks exact byte lengths/SHA-256 hashes and checks report fields. It parses only the generated HTML as text, requiring a finite inert tag set and no active URLs/events/assets, SVG or script embedding. The deliberately escaped reference is an invented reserved example.invalid URL and remains text. No input SVG is rendered.

Default review output omits raw reference/ID strings; private detail mode adds them. Both retain source-identifying hashes/structure and neither is anonymization or permission to publish. These fictional report trees stay in your private workspace.

PowerShell:

```powershell
& $py -I -B (Join-Path $privateWork 'fictional_walkthrough.py') $source $privateWork
```

Ubuntu:

```sh
"$py" -I -B "$private_work/fictional_walkthrough.py" "$source" "$private_work"
```

```python
import copy
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from xml.parsers import expat

if not __debug__:
    raise RuntimeError("ASSERTIONS_REQUIRED")
if tuple(expat.version_info) < (2, 10, 0):
    raise RuntimeError("EXPAT_SECURITY_UPDATE_REQUIRED")
assert len(sys.argv) == 3
source = Path(sys.argv[1]).resolve()
parent = Path(sys.argv[2]).resolve()
assert source.is_dir() and parent.is_dir()
assert not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)()
runtime_names = ("svg_inspector.py", "examples/make_demo.py")
runtime = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
           for name in runtime_names}
work = Path(tempfile.mkdtemp(prefix="fictional-svg-", dir=parent))
assert not work.is_relative_to(source)
protected = {}
outcomes = []
reports = []

def metadata(path):
    info = path.stat()
    return (info.st_size, info.st_mtime_ns, info.st_ino, info.st_nlink,
            info.st_birthtime_ns if os.name == "nt" else info.st_ctime_ns)

def protect(root):
    paths = root.rglob("*") if root.is_dir() else [root]
    for path in paths:
        assert not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()
        if path.is_file():
            protected[path] = (path.read_bytes(), metadata(path))

def invoke(label, program, arguments, expected, exit_code=0, *, sorted_output=True):
    done = subprocess.run([sys.executable, "-I", "-B", str(source / program),
                           *map(str, arguments)], cwd=work, stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=30)
    assert done.returncode == exit_code, (label, done.returncode)
    assert done.stderr == b"", label
    assert done.stdout == (json.dumps(expected, sort_keys=sorted_output)
                           + os.linesep).encode("utf-8"), label
    assert all(path.read_bytes() == value[0] and metadata(path) == value[1]
               for path, value in protected.items()), label
    assert runtime == {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                       for name in runtime_names}
    outcomes.append(dict(case=label, exit_code=exit_code, stdout=json.loads(done.stdout)))

class StaticReportHTML(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag in {"html", "meta", "title", "style", "h1", "h2", "p", "strong",
                       "code", "pre", "table", "thead", "tr", "th", "tbody", "td"}, tag
        assert not any(name.lower().startswith("on") or name in {"href", "src", "srcdoc"}
                       for name, value in attrs)

def inspect(label, svg, expected, exit_code, *, details=False):
    output = work / (label + "-report")
    args = ["--svg", svg, "--output", output]
    if details:
        args.append("--include-details")
    invoke(label, "svg_inspector.py", args, expected, exit_code)
    assert {path.name for path in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    payloads = {name: (output / name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output / "MANIFEST.json").read_bytes()) == dict(schema_version=1,
        files=[dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
               for name, data in sorted(payloads.items())])
    report = json.loads(payloads["report.json"])
    assert set(report) == {"schema_version", "tool", "status", "source_sha256", "source_bytes",
        "parser_expat", "details_included", "node_count", "attribute_count", "text_characters",
        "dimensions", "ids", "references", "findings", "coverage_issues", "limits", "interpretation"}
    assert report["schema_version"] == 1 and report["tool"] == "svg-content-inspector"
    assert report["source_sha256"] == hashlib.sha256(svg.read_bytes()).hexdigest()
    assert report["source_bytes"] == len(svg.read_bytes())
    assert report["parser_expat"] == ".".join(map(str, expat.version_info))
    assert report["details_included"] is details
    assert report["status"] == expected["status"] and report["node_count"] == expected["node_count"]
    assert len(report["references"]) == expected["reference_count"]
    assert len(report["findings"]) == expected["finding_count"]
    assert report["coverage_issues"] == expected["coverage_issues"]
    assert str(work) not in payloads["report.json"].decode("utf-8")
    html = payloads["report.html"].decode("utf-8")
    parser = StaticReportHTML(convert_charrefs=True)
    parser.feed(html)
    parser.close()
    assert "<svg" not in html.lower() and "<script" not in html.lower()
    assert "url(" not in html.lower() and "@import" not in html.lower()
    assert "default-src &apos;none&apos;" in html
    assert "Nothing was rendered, fetched, opened as a reference, executed or sanitized." in html
    reports.append(output)
    protect(output)
    return report, html

demo = work / "new-demo"
invoke("create-fictional-demo", "examples/make_demo.py", ["--destination", demo],
       dict(status="FICTIONAL_FIXTURES_CREATED", files=2), sorted_output=False)
assert {path.name for path in demo.iterdir()} == {"clean.svg", "review.svg", "README.txt"}
protect(demo)
clean_expected = dict(status="NO_SCOPE_FINDINGS", node_count=7, reference_count=1,
                      finding_count=0, coverage_issues=[])
clean, clean_html = inspect("clean", demo / "clean.svg", clean_expected, 0)
assert clean["references"][0]["resolution"] == "resolved_unique"
review_expected = dict(status="REVIEW_REQUIRED", node_count=9, reference_count=3,
    finding_count=10, coverage_issues=["CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED"])
review, review_html = inspect("review", demo / "review.svg", review_expected, 1)
assert all("reference_text" not in row for row in review["references"])
assert all("id_text" not in row for row in review["ids"])
assert "Fictional-empty-placeholder" not in review_html
details, details_html = inspect("private-details", demo / "review.svg", review_expected, 1, details=True)
public_equivalent = copy.deepcopy(details)
public_equivalent["details_included"] = False
for row in public_equivalent["references"]:
    row.pop("reference_text")
for row in public_equivalent["ids"]:
    row.pop("id_text")
assert public_equivalent == review
assert "Fictional-empty-placeholder" in details_html

escaping = work / "escaping.svg"
escaping.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.invalid/fictional?x=&quot;&amp;y=&lt;tag&gt;&#9;end"/><g id="private&#9;identifier"/></svg>\n')
malformed = work / "malformed.svg"
malformed.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><g></svg>\n')
doctype = work / "doctype.svg"
doctype.write_bytes(b'<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"/>\n')
for path in (escaping, malformed, doctype):
    protect(path)
escape_expected = dict(status="REVIEW_REQUIRED", node_count=3, reference_count=1,
    finding_count=0, coverage_issues=["ID_TEXT_OUTSIDE_FRAGMENT_SUBSET", "REFERENCE_TEXT_UNSUPPORTED"])
escaped, escaped_html = inspect("escaping-details", escaping, escape_expected, 1, details=True)
assert escaped["references"][0]["reference_text"] == 'https://example.invalid/fictional?x="&y=<tag>\tend'
assert '&lt;tag&gt;\\u0009end' in escaped_html
assert escaped["ids"][0]["id_text"] == "private\tidentifier"

def refuse(label, svg, output, code):
    invoke(label, "svg_inspector.py", ["--svg", svg, "--output", output],
           dict(status="INCOMPLETE", error=code), 2)

refuse("refuse-malformed-xml", malformed, work / "not-created-malformed", "INVALID_XML")
refuse("refuse-doctype", doctype, work / "not-created-doctype", "DTD_AND_ENTITIES_REJECTED")
refuse("refuse-existing-report", demo / "clean.svg", work / "clean-report", "OUTPUT_EXISTS")
refuse("refuse-missing-parent", demo / "clean.svg", work / "missing-parent" / "report", "IO_OR_METADATA_ERROR")
invoke("refuse-invalid-arguments", "svg_inspector.py", [], dict(status="INCOMPLETE", error="ARGUMENTS_INVALID"), 2)
invoke("refuse-existing-demo", "examples/make_demo.py", ["--destination", demo],
       dict(status="INCOMPLETE", error="FRESH_TRUSTED_DESTINATION_REQUIRED"), 2, sorted_output=False)
assert {path.name for path in work.iterdir()} == {"new-demo", "escaping.svg", "malformed.svg", "doctype.svg",
    "clean-report", "review-report", "private-details-report", "escaping-details-report"}
assert len([path for path in work.rglob("*") if path.is_file()]) == 18
assert not list(work.rglob("*.pyc")) and not list(work.rglob("__pycache__"))
assert len(outcomes) == 11 and len(reports) == 4
print(json.dumps(dict(outcomes=outcomes, reports_verified=4, fixture_files_preserved=6,
    expected_workspace_files=18, unexpected_application_files=0, bytecode_files=0,
    runtime_bytes_preserved=True, source_svg_rendered=False, real_artwork_used=False), sort_keys=True, indent=2))
```

## Complete CLI outcomes

Each stdout object below is the entire decoded output for that invocation. The wrapper prints all eleven outcomes and the preservation checks; it verifies complete report and HTML bytes through independent manifests. The actual parser version is retained in report.json.

```json
[
  {
    "case": "create-fictional-demo",
    "exit_code": 0,
    "stdout": {
      "status": "FICTIONAL_FIXTURES_CREATED",
      "files": 2
    }
  },
  {
    "case": "clean",
    "exit_code": 0,
    "stdout": {
      "status": "NO_SCOPE_FINDINGS",
      "node_count": 7,
      "reference_count": 1,
      "finding_count": 0,
      "coverage_issues": []
    }
  },
  {
    "case": "review",
    "exit_code": 1,
    "stdout": {
      "status": "REVIEW_REQUIRED",
      "node_count": 9,
      "reference_count": 3,
      "finding_count": 10,
      "coverage_issues": [
        "CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED"
      ]
    }
  },
  {
    "case": "private-details",
    "exit_code": 1,
    "stdout": {
      "status": "REVIEW_REQUIRED",
      "node_count": 9,
      "reference_count": 3,
      "finding_count": 10,
      "coverage_issues": [
        "CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED"
      ]
    }
  },
  {
    "case": "escaping-details",
    "exit_code": 1,
    "stdout": {
      "status": "REVIEW_REQUIRED",
      "node_count": 3,
      "reference_count": 1,
      "finding_count": 0,
      "coverage_issues": [
        "ID_TEXT_OUTSIDE_FRAGMENT_SUBSET",
        "REFERENCE_TEXT_UNSUPPORTED"
      ]
    }
  },
  {
    "case": "refuse-malformed-xml",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "INVALID_XML"
    }
  },
  {
    "case": "refuse-doctype",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "DTD_AND_ENTITIES_REJECTED"
    }
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "OUTPUT_EXISTS"
    }
  },
  {
    "case": "refuse-missing-parent",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "IO_OR_METADATA_ERROR"
    }
  },
  {
    "case": "refuse-invalid-arguments",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "ARGUMENTS_INVALID"
    }
  },
  {
    "case": "refuse-existing-demo",
    "exit_code": 2,
    "stdout": {
      "status": "INCOMPLETE",
      "error": "FRESH_TRUSTED_DESTINATION_REQUIRED"
    }
  }
]
```

The workspace has exactly eighteen files: six fictional fixtures and four three-file report trees. Expected refusals create no additional paths. Source/runtime bytes and existing reports remain unchanged, with no bytecode or unexpected application files accepted.

These eleven cases do not inject a late output failure. Such a failure can retain a new incomplete private directory and returns exit 2; it must never be described as a completed inspection. Keep it private and choose a different new destination for a retry. The tool does not overwrite, clean up or roll back files. Native failure/partial-output controls are separate qualification cases.

Inspect only stable trusted local text with one operator. Version checks, DTD refusal and bounded parser callbacks do not certify safe rendering, sanitization, complete standards validity or freedom from parser defects. Sampled filesystem checks are not atomic snapshots, a hostile-filesystem sandbox or hard native I/O deadlines. Read [current qualification](docs/QUALIFICATION.md), [private workspace guidance](docs/PRIVATE-WORKSPACE.md) and the preserved [format reference](docs/FORMAT.md). Historical example/format/validation notes retain the old parser floor; 2.10.0 applies to this release.
