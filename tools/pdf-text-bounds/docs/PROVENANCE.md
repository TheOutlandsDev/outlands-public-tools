# Source provenance and license scope

The owner held a portfolio QA helper that compared pdfplumber character boxes
with page dimensions and a one-point allowance. This public tool is a fresh,
reusable implementation of that generic inspection mechanism, with AI
assistance. It adds explicit nonzero/rotated page boxes, crop intersection,
coverage states, resource/process bounds, private geometry-only reports, tests
and instructions. The historical helper remains unchanged and private.

No original portfolio PDFs, resumes, business/employer content, artwork, private
paths, source receipts or generated document text were copied into the module.
Examples are hand-authored minimal PDF syntax with fictional text and a standard
Helvetica declaration. The test-only pypdf library generates an encrypted version
of an original fixture to prove refusal; no real password or encrypted document
is included. Test binaries/PDF outputs remain in private temporary workspaces.

The [MIT license](../LICENSE) covers original program code, tests, documentation
and authored fixture-generation source. It does not relicense Python, installed
PDF libraries, their native components/fonts, or user inputs. No dependency
implementation or wheel is vendored. See [dependency records](DEPENDENCIES.json)
and [third-party notices](../THIRD-PARTY-NOTICES.txt).

## Primary references checked during development

- [pdfplumber documentation](https://github.com/jsvine/pdfplumber/blob/stable/README.md)
  describes character geometry and page/bounding-box behavior.
- [Pinned pdfplumber distribution record](https://pypi.org/project/pdfplumber/0.11.10/)
  and its installed Page/PDF implementation establish the tested coordinate and
  incremental lifecycle behavior.
- [pdfminer.six documentation](https://pdfminersix.readthedocs.io/)
  and [source/license](https://github.com/pdfminer/pdfminer.six) describe the
  underlying parser; the public inspector does not copy that implementation.

These sources explain supported library mechanisms. They do not certify safe
processing of malicious PDFs or every PDF producer, visual layout, OCR, printing
or document rights. The initial supported/tested versions are explicit rather
than a claim of universal format compatibility.
