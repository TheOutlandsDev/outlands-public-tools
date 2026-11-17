# Run Artifact Manifest Builder 0.1.0

Download the source ZIP and SHA256SUMS.txt from the release. Compare its SHA-256
with the checksum before extracting it. Obtain Python separately: the release
contains source only, with no interpreter or pip dependencies.

Run from the extracted tool directory, using Python 3.12–3.15:

```text
python -E -s -B artifacts.py --selection examples/selection.json --item code examples/code.txt --item configuration examples/configuration.json --item mapping examples/mapping.json --item preview examples/preview.json --item receipt examples/receipt.json --item reconciliation examples/reconciliation.json --item result examples/result.json --item schema examples/schema.json --item source examples/source.txt
```

The fictional example returns PASS (exit 0). Its report contains the complete
embedded manifest, the raw selection hash and the canonical manifest hash.
Artifacts are sorted by symbolic ID. Sizes and hashes are computed from actual
selected bytes; roles are caller declarations. A code artifact is hashed without
being imported or executed. No directory discovery or body-supplied path occurs.

Add `--out` followed by a new absolute report filename beneath an existing,
trusted directory outside the extracted source. The report contains a manifest;
it is not itself a bare manifest. Preserve its embedded manifest with the exact
`toolkit.encode(report['manifest'])` serialization when passing its canonical pin
to another checker. Pretty-printing those bytes changes their raw hash.

The following self-contained fictional exercise creates files only under a new
temporary directory. Save it outside the source as `fictional_manifest_demo.py`.
Run `python -E -s -B fictional_manifest_demo.py` followed by the extracted tool
directory. It independently checks the complete report and a no-overwrite refusal.

```python
import hashlib, json, pathlib, subprocess, sys, tempfile
app = pathlib.Path(sys.argv[1]).resolve()
def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
with tempfile.TemporaryDirectory(prefix='fictional-manifest-demo-') as directory:
    root = pathlib.Path(directory)
    data = b'Fictional data\n'
    (root / 'source.bin').write_bytes(data)
    selection = {'format': 'outlands-run-artifact-selection-v1', 'run_id': 'fictional-run', 'artifacts': [{'id': 'source', 'role': 'input'}]}
    selected = encode(selection)
    (root / 'selection.json').write_bytes(selected)
    args = [sys.executable, '-E', '-s', '-B', str(app / 'artifacts.py'), '--selection', str(root / 'selection.json'), '--item', 'source', str(root / 'source.bin')]
    result = subprocess.run(args, capture_output=True, check=True)
    manifest = {'format': 'outlands-run-artifact-manifest-v1', 'run_id': 'fictional-run', 'artifacts': [{'id': 'source', 'role': 'input', 'bytes': len(data), 'sha256': sha(data)}]}
    expected = {'status': 'PASS', 'format': 'outlands-run-artifact-build-v1', 'selection_sha256': sha(selected), 'manifest': manifest, 'manifest_sha256': sha(encode(manifest)), 'source_paths_recorded': False, 'content_privacy_verified': False, 'target_changes_performed': False}
    assert result.stderr == b'' and json.loads(result.stdout) == expected
    report = root / 'report.json'
    subprocess.run(args + ['--out', str(report)], capture_output=True, check=True)
    assert report.read_bytes() == encode(expected)
    refused = subprocess.run(args + ['--out', str(report)], capture_output=True)
    assert refused.returncode == 2 and json.loads(refused.stdout)['status'] == 'ERROR'
    assert report.read_bytes() == encode(expected)
    assert (root / 'source.bin').read_bytes() == data
print('Fictional manifest and no-overwrite checks passed')
```

Limits: 1–16 artifacts, at most 4 MiB each and 16 MiB combined; exact selected
bindings, valid unique IDs and supported roles are mandatory. Empty bytes and
identical bytes under distinct IDs are permitted. Duplicate JSON keys, floats,
unknown fields and malformed bounded contracts are refused. Exit 2 is a fixed
input/output refusal, exit 130 an interruption. This builder normally returns
PASS or refusal; it does not independently assess content or role correctness.

Use trusted, quiescent files and parents. Existing output leaves, hardlinked
inputs, linked parents and output inside the source are refused. Windows uses
the reviewed CREATE_NEW/OPEN_REPARSE_POINT safeguard. Failed output may retain an
unconfirmed partial file; inspect it privately and choose a fresh filename.
Sequential file observations are not an atomic snapshot or hostile-writer
containment. Parser bounds are cooperative rather than OS resource quotas.

Path omission and hashes do not anonymize IDs, lengths, hashes or relationships.
Keep real selections, artifacts and reports private. A matching manifest does
not establish source authority, actual run execution, provenance authenticity,
privacy approval or permission to publish. The receipt reconciler and provenance
checker remain separately invoked tools; this builder does not perform their work.

See [qualification](docs/QUALIFICATION.md), [original validation](VALIDATION.md)
and [I/O limits](IO-SAFETY.md). Release VALIDATION.json records actual eight-lane
archive results. Complete pinned SDK downloads are separate from this source ZIP.
