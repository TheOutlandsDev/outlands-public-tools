# Steven Chat / Stephen — 1.0.0

A bounded terminal chat client for an independently managed local HTTP backend.
Python 3.12 or newer, standard library only, original [MIT source](LICENSE).
The deterministic `--demo` works without a backend, model or login. Connected
commands require explicit `--connect`; this client never installs/starts Ollama,
downloads a model or executes generated text.

## Download and fictional walkthrough

Download the [1.0.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/steven-chat-v1.0.0):
ZIP, checksums, usage guide, public validation JSON and build manifest. The ZIP
contains 36 reviewed source files plus their manifest, 37 members; Python,
Ollama, model weights, real conversations, environments and raw logs are excluded.
Verify hashes before extracting into a fresh owned directory. No pip package,
administrator access or login is required for the demo or fictional fixture checks.
Keep the `steven` package and all three alias scripts together.

The [executable fictional guide](USAGE.md) uses copied runtime and its own bounded
temporary loopback HTTP fixture. It checks exact requests, plain-text replies,
context trimming, explicit fresh saves/resume, terminal controls and refusals.
Its fixture produces authored responses; no actual Ollama or model is used.

From this module directory:

```powershell
python -E -s -B -m steven --demo
python -E -s -B main.py --demo
```

On Ubuntu, use the selected `python3` command with the same arguments. The
`chatbot.py` and `stephen.py` aliases call the same terminal entry point. Running
without a command prints help; no request or automatic session save occurs.

## Explicit connection and session behavior

After separately choosing/configuring an approved backend and installed model,
replace `INSTALLED_LOCAL_MODEL` with its exact name. These manual commands make
requests only when you choose to run them; qualification uses a fixture instead:

```text
python -E -s -B -m steven models --connect --endpoint http://127.0.0.1:11434
python -E -s -B -m steven ask --connect --model INSTALLED_LOCAL_MODEL --prompt "A fictional question"
python -E -s -B -m steven chat --connect --model INSTALLED_LOCAL_MODEL
```

Only literal HTTP loopback origins `127.0.0.1`, `localhost` and `[::1]` with a
supported port are accepted. Environment proxies and HTTP redirects are disabled.
Obvious cloud-labelled model names are refused/filtered. A local endpoint or
ordinary model name does not attest the backend's own outbound routing, privacy,
liveness or actual model availability. Configure/review that service separately.
There is no Bedrock, OpenAI, Kiro, cloud routing, agent/tool execution or sandbox.

Add `--session EXPLICIT_EXISTING_JSON` to resume schema-1 history and
`--save NEW_JSON` to create a new checkpoint. The model must match the session.
Existing saves are refused rather than overwritten. A save is attempted after a
successful reply, so a refused save can still follow a completed backend request
and printed answer. Parent directories must already exist. Relative paths are
accepted; this client does not provide the stronger absolute-path/UNC/stream or
atomic stable-snapshot contract of some inspectors in this repository.

Interactive `/help`, `/clear` (also `/reset`) and `/exit` (also `/quit`, `exit`,
`quit`) are local commands. Clear retains an initial system message and changes
only memory. Failed turns are not appended. Normal quit/EOF with `--save` writes
once after at least one successful turn; Ctrl+C exits 130 without automatic save.
With no `--save`, the client creates no transcript file. Terminal/backend/OS
records are outside that behavior.

Sessions contain prompts and answers in plaintext. Terminal control/bidi characters
are escaped for display, but stored text retains its original characters. POSIX
fresh-file creation requests mode 0600; Windows inherits filesystem permissions.
No encryption, anonymization, secure erasure, Windows ACL hardening or backend-log
privacy is provided. Read [SECURITY.md](SECURITY.md) before using private content.

## Bounds and failure limits

| Item | Bound / behavior |
| --- | --- |
| Python qualification | Pinned 3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu. |
| `--timeout` | Finite 1–300 seconds for underlying HTTP operations; not a hard whole-process deadline. |
| `--context-chars` | 1,024–65,536 content characters, not a tokenizer budget; whole old pairs are dropped first, keeping an initial system message. |
| `--max-output-tokens` | Integer 1–4,096 passed as the requested `num_predict`; generation depends on the backend. |
| Prompt/system | At most 8,192 characters each. |
| Session/context | At most 128 messages and 65,536 content characters; complete alternating turns after an optional initial system message. |
| HTTP response/session file | At most 1 MiB; expected strict UTF-8 JSON without duplicate keys/nonfinite constants. |
| Reply | Completed plain-text assistant message; no tool calls or generated-code execution. |
| File saves | Fresh exclusive creation; linked paths/parents refused where supported; flush/fsync does not make a rollback transaction. |

The newest request/reply is never silently dropped to meet context limits.
Malformed, partial, oversized or mismatched sessions are refused. Input reads are
bounded regular-file reads, not atomic snapshots against a hostile writer.
Concurrent path changes and I/O failures remain limitations. A failed new save
may leave a partial file; inspect it privately and choose a new destination.

Exit 0 covers normal help/demo/chat, including interactive retry after a failed
turn. Command/validation/backend failures exit 2. Ctrl+C exits 130; interruption
does not guarantee the separately managed backend immediately stops its work.

## Qualification and contributions

The [qualification contract](docs/QUALIFICATION.md) separates 75 unchanged original
tests from 30 copied-runtime checks per lane and the independent fictional guide.
Actual release `VALIDATION.json` records outcomes, skips and byte identities.
No fixture result proves real model inference, quality, hardware/GPU compatibility,
backend cloud isolation or license/rights suitability of a selected model.
The preserved [historical validation](docs/VALIDATION.md) and
[dependency record](docs/DEPENDENCIES.json) describe an earlier 0.1.0 review;
the unchanged runtime and this release identify as 1.0.0.

[Contribute](CONTRIBUTING.md) with a fictional reproduction and exact source,
Python/OS versions. Exclude actual transcripts, endpoints, account data, machine
paths, model weights and server logs. The full-repository suggestion/bug templates
are available through the repository's GitHub Issues page.
