# Install and use the API request-and-response tools

Review an interface definition, supplied requests, supplied responses and changes
between versions. Start with the [plain-language definitions and method](../../methodology/API-EXCHANGE.md)
and [machine-readable component guide](components.json). Each independent MIT wheel
provides its own command, embedded fictional examples and Python API. Supply Python
3.12 or 3.13; runtime dependencies are standard library only.

| Tool | When to use it | Fictional example and expected output | What its result establishes |
| --- | --- | --- | --- |
| [Operation contract checker](../../tools/api-operation-contract-checker/README.md) | Review declared field rules and answer variants before writing cases. | An invented service-proposal definition PASSes; overlapping routes require review and withhold assessment. | Consistency of a bounded declaration format. |
| [Request checker](../../tools/api-request-contract-checker/README.md) | Check proposed inputs against one exact definition. | Priority 2 within 1..5 PASSes. Priority 6 is invalid and REVIEW_REQUIRED, even when expected invalid. | Validity of supplied structured inputs against selected rules. |
| [Response checker](../../tools/api-response-contract-checker/README.md) | Check supplied answers and request coverage. | A declared 200 answer for the valid request PASSes; a declared 400 error for an invalid request can also PASS. | Declared response validity, distinct from request validity or successful work. |
| [Version/scenario comparator](../../tools/api-exchange-scenario-comparator/README.md) | Reassess the same cases under a changed definition. | Unchanged outcomes PASS; tightening the priority maximum changes validation and requires review. Missing/changed cases remain incomparable. | Selected-case outcome equality, not whole-interface compatibility. |

All inputs are assertions. No network request, server, authentication or service
action occurs. A response PASS can describe an error; a comparison PASS can describe
matching expected-negative cases. Inspect the individual validity fields. Reports
retain IDs/hashes and do not anonymize project data.

## Install one tool or all four

Download selected wheels and SHA256SUMS.txt from the immutable
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/api-exchange-wheels-v1.0.0).
Verify hashes before installing. Create a fresh ENV outside the checkout with
`py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu, then use
that environment's Python and scripts directory. Choose one of these installs:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_api_request_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-api-exchange-collection==1.0.0
```

The collection requires all five release wheels in WHEEL_DIRECTORY; exact-version
dependencies resolve offline. `outlands-api-exchange` lists the four commands.
`outlands-api-request-contract-checker-demo` runs bundled fictional input.
`outlands-api-request-contract-checker --input PRIVATE_JSON` checks selected input.
Use components.json to substitute another individual filename or command.

On Windows, use `ENV/Scripts/python.exe` and commands in `ENV/Scripts`; on Ubuntu,
use `ENV/bin/python` and commands in `ENV/bin`. These are downloadable wheels;
package-index registration is not implied. Existing complete source downloads
remain a separate option in each tool's catalog entry.

## Call a tool from another project

The APIs are `operations.check`, `requests.check`, `responses.check` and
`scenarios.check` in distinct `outlands_TOOL` packages. Each accepts raw JSON bytes
and returns a report dictionary. The request module belongs to this wheel and has
no dependency on the third-party Requests HTTP library.

```python
from importlib.resources import files
from outlands_api_request_contract_checker.requests import check

raw = files("outlands_api_request_contract_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["requests"][0]["valid"] is True
assert report["network_requests_performed"] is False
assert report["service_behavior_verified"] is False
```

For actual project data, replace the embedded example read with your own reviewed
JSON byte input. Catch `outlands_api_request_contract_checker.toolkit.Rejected`
for refused input. Status REVIEW_REQUIRED is a returned report, not an exception.
CLI exits are 0 PASS, 1 REVIEW_REQUIRED, 2 refusal and 130 interruption. Output is
JSON on stdout; the source guide documents guarded fresh `--out` destinations.

## Worked request-to-response review

After installing all four, run
`python -B integrations/api-exchange/exercise.py` from the repository root. The
script uses installed packages and their embedded examples, not repository imports
or live endpoints. It performs these observations:

1. All four invented HVAC service-proposal examples PASS and share the appropriate
   normalized operation/request/response cohort pins.
2. Priority 6 is an invalid request. Its explicit 400 error observation passes
   response review while retaining `request.valid == false`.
3. Tightening the allowed priority maximum from 5 to 1, repinning the selected
   operation and dependent request, changes validation for the same priority-2 case.
4. Changing the candidate payload makes it a different case; dropping its response
   leaves a coverage gap. Neither yields a clean comparison.
5. Stale pins and conflicting identities withhold assessment. Identical top-level
   declarations count once; duplicate nested fields reject the whole operation.
6. Equal expected-negative cases can pass comparison without accepting traffic.

The exercise prints a concise assertion summary. It performs no HTTP, target
updates or service execution. The complete inputs and precise output schemas are
in the [four source guides](components.json).

## Relationship to Data & Services Stack

[Data & Services Stack](../../systems/data-services-stack/README.md) has a separate
loopback browser API. Its public `data_services/web.py` uses `/api/` actions,
Host/Origin/session checks, Content-Type/Length framing and a nested `{result: ...}`
success envelope, with `{code: ...}` errors. These tools do not accept that API's
raw traffic or nested results directly. Their symbolic path arrays, flat scalar
bodies and restricted custom headers have different semantics.

A useful future use case is reviewing a deliberately selected scalar projection
of a proposed action and its example outcomes before changing the browser API.
A caller-reviewed mapping must specify action/route and method, exact operation
identity/revision, projected fields/types/requiredness, absent versus empty bodies,
status/error variants, request expectations, response coverage, and normalization
and hash domains. Dropped nested fields must be explicit; projected consistency
does not prove whole-response correctness. Never put a real session token in
examples or reports. Token authenticity, origin, HTTP framing and actual service
effects remain separate tests, outside this format.

No adapter or live system integration is included. The worked HVAC proposal is
fictional and is not asserted to be a Data & Services Stack endpoint. Real project
configuration, request bodies, tokens, journals and output remain private.

## Build and qualification

Use Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute
output directories outside the checkout, then run:

```text
python -B integrations/api-exchange/build_wheels.py --output OUTPUT_DIRECTORY
python -B integrations/api-exchange/verify_wheels.py --wheels OUTPUT_DIRECTORY
```

Build verifies exact public SOURCE-MANIFEST pins for the selected entry,
toolkit.py, native_windows.py, decision_core.py, api_core.py, fictional JSON
examples, README and MIT license. Package-relative imports isolate each wheel;
the existing tool source is unchanged. ZIP headers are fixed synthetic metadata;
standard package/license metadata and attribution remain. SHA256SUMS.txt and
release.json pin the exact wheel/manifest bytes.

Qualification checks the existing 13 standalone/cross-tool acceptance methods,
fresh individual/collection CLI/demo/API/review cases, this guide's literal API
snippet and the installed exercise. Two local builds and Windows/Ubuntu Python
3.12/3.13 builds compare exact bytes. Anonymous public-download installs repeat
after publication. These are package and fictional-contract checks, not live
traffic, wire-protocol, authorization or whole-service validation.
