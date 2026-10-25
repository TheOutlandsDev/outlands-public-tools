# OUTLANDS | Steven Chat

Steven Chat is a small terminal client for a separately managed local Ollama
server. It continues the owner's chatbot project, which was also called
**Stephen**. It keeps conversation context, lets you choose an installed model,
and supports explicit session import and save. The application uses Python's
standard library; it does not install Ollama, select/download a model, or start
a server.

The original source, tests, documentation and fictional examples in this folder
are [MIT licensed](LICENSE), as part of
[OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools).
The server and every selected model retain their own licenses. No model weights,
old virtual environment, real conversation or user-specific configuration is
included. See [provenance](docs/PROVENANCE.md) and
[dependency records](docs/DEPENDENCIES.json).

**Validation boundary:** automated tests use generated conversations, simulated
failures and a real loopback HTTP fixture. They do not establish model quality,
GPU compatibility or inference with an actual Ollama/model installation. Real
model inference remains unverified for this release. See
[validation](docs/VALIDATION.md).

## Start without a model

Install Python **3.12 or 3.13**, clone/download the collection, and open a terminal
in `tools/steven-chat`. No `pip install` command is needed for this client.

```text
python -m steven --help
python -m steven --demo
python -B -m unittest discover -s tests -v
python -B source_check.py
```

The demo prints a clearly marked fictional exchange. It makes no HTTP request,
starts no server, loads no model and writes no conversation. Automated tests can
start temporary loopback fixture servers and create disposable test files.

`main.py`, `chatbot.py` and `stephen.py` are compatibility entry points for the
same application. For example, `python stephen.py --demo` uses the same offline
demo. Importing the package does not initialize a model.

Calling `python -m steven` without a subcommand displays help and makes no
connection. Common options can appear before or after the subcommand.

## Prepare a local server separately

1. Install Ollama using its [official instructions](https://ollama.com/download).
2. Review the selected model's license, hardware requirements and download size.
   Obtain a model separately using the model publisher's/Ollama's instructions.
   Steven never pulls models or accepts license terms for you.
3. Disable Ollama cloud features **in the server's configuration/environment**
   before starting or restarting that server. Ollama documents
   `OLLAMA_NO_CLOUD=1` and `disable_ollama_cloud` in its
   [FAQ](https://docs.ollama.com/faq). Merely setting an environment variable in
   Steven's shell does not reconfigure an already running server.
4. Use a trusted server listening only on loopback. Confirm that your chosen model
   is installed locally; avoid cloud model aliases. Steven rejects obvious
   `:cloud`/`-cloud` names, but that name check is not an isolation guarantee.

For a **separately started** server, the environment setting can be supplied in
its own terminal. Close an existing server first using its normal controls to
avoid starting a second instance.

PowerShell:

```powershell
$env:OLLAMA_NO_CLOUD = '1'
ollama serve
```

POSIX shell:

```sh
OLLAMA_NO_CLOUD=1 ollama serve
```

These are manual setup examples, not commands run by Steven. Check Ollama's
current documentation for the installed version and verify its cloud-disabled
status. The client cannot prove that a backend, proxy, container or operating
system never forwards or logs a request. It also cannot establish a model's
license from its display name.

## Connect and choose a model

Every network operation requires **`--connect`**. The default endpoint is
`http://127.0.0.1:11434`. Only loopback HTTP endpoints are accepted: `127.0.0.1`,
`[::1]`, or `localhost` (normalized to `127.0.0.1`), with an optional port.
Remote hosts, HTTPS, URL credentials, query strings, fragments and base paths are
unsupported. Environment proxy settings and HTTP redirects are not used.

```text
python -m steven models --connect
python -m steven ask --connect --model MODEL_NAME --prompt "Explain a Python list in two sentences."
python -m steven chat --connect --model MODEL_NAME
```

Replace `MODEL_NAME` with the exact installed local model name returned by the
first command. No model is selected by default. The fictional label
`example-local:tiny` in the examples is **not a recommended or downloadable model**.

With a server on another local port:

```text
python -m steven models --connect --endpoint http://127.0.0.1:11435 --timeout 20
python -m steven ask --connect --model MODEL_NAME --prompt "Give three names for a fictional garden." --max-output-tokens 128 --context-chars 8192
```

The client calls Ollama's documented
[`GET /api/tags`](https://docs.ollama.com/api/tags) and
[`POST /api/chat`](https://docs.ollama.com/api/chat) endpoints. Chat requests use
`stream:false` and do not register tools. Model output is treated as text; it is
never executed as Python, a shell command, a file operation or a browser action.

## Conversation context and sessions

Without session arguments, chat exists only in process memory. The current
conversation is sent to the selected server on each turn. The client removes
old complete user/assistant pairs when necessary to meet its character budget;
an initial system message is retained. A character budget is not a tokenizer or
a guarantee that a model's token window will fit. Failed requests do not append
the failed user turn as though it succeeded.
If the newest user/reply exchange plus any system message exceeds the budget,
the exchange is rejected; its text is not silently truncated into the history.

Use explicit session paths to continue a conversation or save it. Saving creates
a **new file**; existing files are never overwritten. Use a new output filename
for each checkpoint. Paths below are fictional private examples; place real
conversations outside this source folder and outside a public repository.

```text
python -m steven ask --connect --model MODEL_NAME --prompt "List two fictional project names." --save ../private-chat-001.json
python -m steven chat --connect --model MODEL_NAME --session ../private-chat-001.json --save ../private-chat-002.json
```

An imported session must have the expected schema, valid text/roles and complete
alternating conversation pairs. Its model must match `--model`; start a fresh
session when switching models. The [fictional session](examples/session.json)
documents the format. It does not prove compatibility with any actual model.

In interactive chat, `/help` shows commands, `/clear` (also `/reset`) resets in-memory history
while retaining an initial system message, and `/exit` or `/quit` ends the chat.
Plain `exit` and `quit` are retained for the old terminal workflow. `/clear` does
not delete any file. With `--save`, a normal quit or end-of-input saves once after
at least one successful exchange. Ctrl+C exits with code 130 and does not save.
Without `--save`, quitting makes no conversation file. A failed interactive turn
reports a generic error and permits another turn without appending the failure.

Session files contain prompts and responses in clear text. POSIX creation uses
owner-only mode; Windows uses inherited filesystem permissions. The client does
not encrypt, anonymize or securely erase histories, terminal scrollback, server
logs or operating-system records. Review [privacy and security](SECURITY.md).

## Limits and troubleshooting

| Option or limit | Supported range / behavior |
| --- | --- |
| Python | 3.12 and 3.13; standard library only. |
| `--timeout` | Finite 1–300 seconds for the underlying HTTP operation; not a hard whole-process deadline. |
| `--context-chars` | 1,024–65,536 content characters; whole old pairs may be trimmed. |
| `--max-output-tokens` | 1–4,096 requested output tokens; the selected backend/model determines generation behavior. |
| Prompt | At most 8,192 characters. |
| Messages/session content | At most 128 messages and 65,536 content characters; invalid or partial conversation records are refused. |
| HTTP response / session file | At most 1 MiB; strict expected JSON shape. |
| Output | Terminal control/ANSI and bidirectional formatting characters are escaped. |
| Files | Explicit reads/saves only; fresh saves, with linked input/parent paths refused. |

If the server cannot be reached, verify its local port and normal startup state;
Steven does not start it automatically. If a model is unavailable, check your
separate installation and exact local model name. Do not change the endpoint to
a public service or bypass a refused cloud alias. If a response/session is
rejected, check its documented schema and size instead of disabling checks.

An invalid entry can cause the model-list response to be refused. Well-formed
names with obvious cloud labels are omitted from the displayed list; this
filter cannot prove that remaining model aliases run locally. A failed save may
leave a partial new file. Inspect that file
privately and choose another fresh output path; existing files are not replaced.

Long replies may be truncated by the requested output-token budget. Client
interruption does not guarantee that a backend stops inference immediately.
Model loading, memory use, supported languages, accuracy and content behavior
depend on the selected model/server; no particular model is endorsed or bundled.

This release has no GUI, speech, web search, file ingestion, training, retrieval,
plugin execution or cloud-provider support. It is a bounded terminal client,
not an autonomous assistant.

Normal exit/help/demo use exit code 0; command/validation/backend failures use
code 2, and Ctrl+C uses 130. Interactive per-turn failures can be followed by
another prompt; they do not immediately terminate the whole chat.

## Suggestions and contributions

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=steven_chat_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=steven_chat_bug.yml).
Include the source commit, Python/OS/server versions, exact commands and a
fictional reproduction. Distinguish fixture results from actual model inference.
Do not attach transcripts, account data, model weights, private paths or server
logs without carefully removing private material. Read [contributing](CONTRIBUTING.md).
