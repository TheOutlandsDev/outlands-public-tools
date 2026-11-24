# Run the Offline Lot Start Reservation Request Validator

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\lot-start-reservation-request-validator-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it with Python 3.12 or 3.15. Install the pinned runtime requirements in a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe lot_start_reservation_request.py examples/fictional-request.json
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python lot_start_reservation_request.py examples/fictional-request.json
```

The example prints the normalized request and the SHA-256 fingerprint of its evidence. Surrounding whitespace is removed from lot IDs and letters become uppercase. The fingerprint uses canonical JSON with sorted object keys and keeps each evidence list's order. Equivalent ID casing and surrounding whitespace produce the same fingerprint. The lookup status is caller-supplied evidence.

Use the example's shape for your saved request. Include the source request key, candidate modality, positive uncovered demand, and all six evidence lists. The original schema accepts 1 to 10,000,000 units of uncovered demand for a reservation. Historical inventory allows up to 5,000 entries, and each other evidence list allows up to 500.

The CLI reads one saved file and prints JSON to stdout. It exits 0 for a valid request and 2 for invalid or unreadable input. It only validates the request and does no reservation, lot generation, or live identity lookup.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
