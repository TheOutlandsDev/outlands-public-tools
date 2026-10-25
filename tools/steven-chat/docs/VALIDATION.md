# Validation record — Steven Chat 0.1.0

## Recorded scope

Local Windows / Python 3.12.7: **75 tests discovered, 73 passed, two skipped**,
with no failures, errors or ResourceWarnings. The skips require Windows symlink
creation permission that this account lacks; they are not counted as passes.
The dedicated CI matrix runs Windows/Ubuntu with Python 3.12/3.13. Read the
linked run for each platform's actual outcome and skips.

The automated suite uses standard-library unit tests, generated session files,
subprocess CLI checks and an actual temporary loopback HTTP fixture. The fixture
implements selected Ollama response shapes; it is not Ollama and performs no
model inference. Test totals and current Windows/Ubuntu outcomes are recorded in
the [GitHub Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions).

Checks cover endpoint restrictions, explicit connection opt-in, request/response
shape, conversation context, malformed/oversized data, session rules, fresh-file
creation and terminal rendering within the actual suite's documented cases.
Source SHA-256 checks, UTF-8 parsing and local document links are reviewed
separately. A manifest establishes selected bytes; it does not prove authorship,
license completeness, absence of every secret or application correctness.

The offline demo is explicitly fictional. No server/model is started or
downloaded by the demo. Tests use disposable inputs and may start local fixture
servers. No real conversation, model corpus, historical environment or installed
Ollama configuration is needed by the tests.

## Unverified runtime behavior

This release has **no real-model inference acceptance result**. Actual server
version compatibility, model loading, generation quality, GPU/CPU memory,
token-window fit, cancellation responsiveness and long-running interactive use
require separate testing with a legally obtained local model. A fixture pass is
not a substitute for those checks. Character limits are not token estimates.

Before reporting a real-model result, record the source commit, OS, Python,
Ollama version, exact model identifier/digest and relevant local configuration.
Verify cloud-disabled server operation and use fictional prompts. Exercise model
listing, two-turn context, `/clear`, normal exit/EOF/interrupt, explicit fresh save,
resume, unavailable-model handling and server shutdown. Retain real transcripts
and operational logs privately; publish only a redacted summary with permission.

No model license or privacy claim follows from a successful response. The client
can restrict its HTTP destination, but cannot attest to the server's outbound
connections, logging or model provenance.
