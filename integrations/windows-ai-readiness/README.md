# Windows 11 AI development readiness

This source-only setup is for a Windows 11 developer workstation. The version
snapshot below was checked on 2026-11-09. Use each project's supported versions
before adopting a newer runtime. No AWS account, secret, model access, or paid
invocation is required for the offline checks.

| Component | Tested version | Purpose |
| --- | --- | --- |
| Python | 3.15.2 | Isolated current-language checks and SDK examples |
| Node.js | 26.13.0 LTS | JavaScript SDK examples |
| Eclipse Temurin JDK | 27.0.1 | Java builds |
| Apache Maven | 3.10.0 | Java dependency/build tool |
| AWS CLI | 2.39.7 | Local command/help checks |
| Kiro CLI / IDE | 3.1.0 / 1.4.121 | Coding workspace |

Get installers from [Python](https://www.python.org/downloads/),
[Node.js](https://nodejs.org/en/download),
[Adoptium](https://adoptium.net/temurin/releases/),
[Maven](https://maven.apache.org/download.cgi),
[AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html),
and [Kiro](https://kiro.dev/docs/getting-started/installation/). Verify the
publisher signature or published digest before installing. Prefer isolated
portable JDK/Node/Maven folders and a Python virtual environment so a project
can retain its own runtime. Run `verify-windows.ps1` with paths to those tools;
the script only reads versions and prints a JSON report.

## Additional Python 3.15 source qualification

The [compatibility report](PYTHON-315-REVIEW.md) distinguishes the original
per-tool run from the follow-up shared suites. Twenty-nine source tools have
their tests under the repository's top-level `tests/` directory. Run their
fixed, reviewed qualification set on Python 3.15 from the collection root:

```text
python -B integrations/windows-ai-readiness/check_shared_python315.py
```

Empty and wholly skipped suites do not qualify. This lane does not change
the Python 3.12/3.13 requirements of the released wheels or certify all newer
third-party dependencies. It executes fictional tests in disposable fixtures.

## Kiro workflow

For a complete project setup, use the [Kiro development kit](../kiro-dev-kit/README.md).
It adds native agents, skills, steering, an installer with rollback, and
separate offline and managed-session qualification. The single prompt below
is only an earlier starter template.

Copy [codex-style.md](templates/codex-style.md) into the target project's
`.kiro/agents/` directory, or into `~/.kiro/agents/` for a personal agent
available across projects. The template asks Kiro to inspect the repository,
make reviewable edits, run meaningful tests, and report evidence and limits.
Kiro also reads project `AGENTS.md` and `.kiro/steering/` files. Select a model
from Kiro's `/model` list after sign-in. Kiro currently documents GPT-5.6 Sol,
Terra, and Luna; GPT-6 is a separate direct Bedrock SDK option. The prompt and
tool workflow can be similar to Codex, but the product, tools, permissions,
models, memory, and execution environment are different.

## Direct Bedrock examples

The Python, Node, and Java examples use the [OpenAI SDK Bedrock
provider](https://developers.openai.com/api/docs/guides/amazon-bedrock) with the
Responses API. They default to local `--check` mode. `--live` is opt-in and
requires your own Bedrock access and an `AWS_BEARER_TOKEN_BEDROCK` environment
variable. Do not put a key, account ID, personal path, or employer content in
the repository. The example selects `openai.gpt-6-sol` in `us-east-1`, as
documented for the Bedrock Mantle endpoint; check regional and account
availability before a live request.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install "openai[bedrock]" boto3
.venv\Scripts\python.exe bedrock_python.py --check
.venv\Scripts\python.exe bedrock_boto3_check.py

npm install --prefix node
node node/bedrock_node.mjs --check

mvn -f java/pom.xml -q compile
java -cp java/target/classes BedrockOpenAI --check
```

The Boto3 check inspects the [Bedrock Runtime service
model](https://docs.aws.amazon.com/code-library/latest/ug/python_3_bedrock-runtime_code_examples.html)
with placeholder credentials and makes no request. The Java `--check` command
verifies a compiled class and JDK. A live Java run
also needs Maven dependency resolution on its classpath; use the Maven exec
plugin or your application's build configuration. These examples are small
starting points, not a replacement for an application's authentication,
network, logging, error handling, or cost controls.

The public-tools install bundle currently supports Python 3.12/3.13. The
[Python 3.15 source/test review](PYTHON-315-REVIEW.md) reports the separate
compatibility exercise; do not bypass package
`Requires-Python` limits or assume third-party dependencies support 3.15.
