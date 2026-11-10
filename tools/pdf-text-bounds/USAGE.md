# PDF Text Bounds Inspector 0.2.0

Download the source ZIP, this guide, build-manifest.json, VALIDATION.json and
SHA256SUMS.txt from the same GitHub release. Verify every listed checksum before
extracting. PowerShell: `Get-FileHash -Algorithm SHA256 ./*.zip`; Ubuntu:
`sha256sum -c SHA256SUMS.txt`. Compare the complete hash, not a prefix.

Use regular CPython 3.12-3.15 on Windows x64 or Ubuntu x86-64. Extract the ZIP
into a directory you control. No administrator permission is inherently needed
for a user-owned Python venv; device policy may still restrict installation.
The ZIP contains original MIT source, tests, docs and fixture generators.
It contains no Python runtime, installed libraries, DLLs, fonts or PDFs.

Open PowerShell in the extracted `pdf-text-bounds-0.2.0` directory. Start with
the [private workspace guide](docs/PRIVATE-WORKSPACE.md), then run:

```powershell
python -m venv "$privateWork/pdf-venv"
$pdfPython = "$privateWork/pdf-venv/Scripts/python.exe"
& $pdfPython -m pip install --require-hashes --only-binary=:all: -r requirements.lock.txt
& $pdfPython -m pip check
& $pdfPython -B examples/make_demo.py --destination "$privateWork/demo"
& $pdfPython -B pdf_bounds.py --pdf "$privateWork/demo/inside.pdf" --output "$privateWork/inside-report"
& $pdfPython -B pdf_bounds.py --pdf "$privateWork/demo/outside.pdf" --output "$privateWork/outside-report"
```

For Ubuntu set `PRIVATE_WORK="$(mktemp -d)"`, create the venv with
`python3 -m venv "$PRIVATE_WORK/pdf-venv"`, and set
`PDF_PYTHON="$PRIVATE_WORK/pdf-venv/bin/python"`. Replace `& $pdfPython`
with `"$PDF_PYTHON"` and `$privateWork` with `$PRIVATE_WORK` in the commands.

Inside: exit 0, 16 characters and zero findings. Outside: expected exit 1,
four characters/four right-side findings. Exit 1 also covers textless pages
that require review. Exit 2 means incomplete input/dependency/parser/limit/IO
processing. Use a new output directory every time; existing outputs are refused.
Open report.html locally. Verify report.json/report.html against MANIFEST.json.

Eight runtime versions remain exact and closed. The hash locks contain the
non-yanked PyPI wheel hashes captured in [WHEELS.json](docs/WHEELS.json).
This allows wheel selection by pip; it does not qualify every wheel platform.
Both pip hash validation and the inspector's version guard fail closed.
Inspecting a PDF is offline; pip installs and the explicitly requested
`check_advisories.py` command use the network. Do not remove pins or use
`--ignore-requires-python` to force an unsupported install.

To test, install `requirements-dev.lock.txt` with the same hash/binary flags,
then run `python -B -W error -m unittest discover -s tests -v` using the venv
interpreter. pypdf is used only for authored encrypted refusal fixtures.
See [qualification](docs/PYTHON315.md) and [license notices](THIRD-PARTY-NOTICES.txt).

Use trusted completed local PDFs only. This checks observed character geometry,
not rendering, OCR, all clipping, fonts, print accuracy or malicious-input safety.
Reports omit text/paths/metadata but preserve document hashes and geometry.
Worker/audit/byte/time bounds do not provide an OS sandbox or hard RAM cap.
Free-threaded Python, other CPU architectures, hostile filesystem races, device
policies and real/private documents remain outside this qualification.
