# Test 002: Secure Subprocess

This standalone eval checks whether an agent can safely replace insecure shell-based subprocess code with a typed, testable, standard-library implementation.

## What to give the agent

Give the agent the whole folder, or specifically these files/folders:

```text
AGENT_PROMPT.md
task.md
starter/
tests/
pyproject.toml
scripts/run_tests.py
```

## Run the test before the agent changes code

From this folder:

```bash
python scripts/run_tests.py
```

The starter implementation is intentionally insecure and should fail the tests.

## Run the test after the agent changes code

From this folder:

```bash
python scripts/run_tests.py
```

The eval passes when all tests pass and the final patch satisfies `scoring.md`.
