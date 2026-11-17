# Start Here

For a first test run, do not try to train the agent on everything. Start with a small, controlled corpus and measure behavior.

## First-run objective

The first run should answer one question:

> Can the agent produce maintainable, typed, tested, secure Python 3.12-style code when given a clear task and a small knowledge base?

## Feed this pack in this order

1. `01_agent_seed/agent_operating_spec.md`
2. `01_agent_seed/python_3127_coding_doctrine.md`
3. `01_agent_seed/retrieval_instructions.md`
4. `02_source_catalog/source_manifest.json`
5. `03_ingestion_templates/metadata_schema.json`
6. `03_ingestion_templates/chunking_policy.md`
7. `04_examples/good/`
8. `04_examples/bad/`
9. `04_examples/refactors/`
10. `05_evals/`

## Good first prompt to test the agent

```text
You are working in a Python 3.12.7 project. Read the task file in 05_evals/eval_001_pathlib_json_loader/task.md. Modify only the starter file unless the task asks for tests. Run the provided tests. Return a short explanation, the diff, and any commands run.
```

## Expected agent behavior

The agent should:

- Inspect the task and tests before editing.
- Make a minimal patch.
- Preserve type annotations.
- Avoid unsafe behavior such as eval, shell=True, or broad exception swallowing.
- Run tests or explain why it could not run them.
- Report assumptions honestly.
