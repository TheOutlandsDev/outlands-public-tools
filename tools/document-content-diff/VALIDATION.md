# Fictional validation and boundaries

From this standalone directory:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Qualification runs Windows/Ubuntu, Python 3.12/3.13, with no third-party runtime
installation. Native link/hardlink fixtures are mandatory in CI using
OUTLANDS_INTAKE_REQUIRE_LINKS=1; unavailable native fixtures fail qualification.
Only opposite-platform methods are skipped there. A local volume that cannot
create the native fixtures may report explicit skips and does not provide that
native proof. Fixed fully spelled runner temp paths preserve alias refusal.

Core tests use invented documents/records and independently mutated OPC/XML.
They check typed accounting or document comparison, malformed/active content,
resource limits, exact values/pins and private diagnostic boundaries. Shared native
I/O tests cover positive ordinary reads/writes, input changes, hardlink/linked-parent
refusal, source protection, fresh output, overwrite refusal and retained failed writes.

From the collection root, actual CLI/copy/interop acceptance is:

```text
python -B -W error -m unittest discover -s tests -p test_document_tools.py -v
```

It runs all four independent copied directories, source manifests, new reports and
overwrite refusals; generates fictional DOCX; exercises intake-to-record-set
reconciliation; and parses a separately generated document from the existing public
Document & Template Workbench writer. Canonical public copy comparison requires
Git checkout metadata. Normal CLI/library use and standalone core tests need no Git.

These checks do not establish general Word/LibreOffice compatibility, GUI rendering,
visible layout, production document support, source authority, business correctness,
network-filesystem support, hostile race containment or power-loss durability.
Parsed content is not anonymized. No original/private document, database, template,
service, configuration or production workflow is exercised.
