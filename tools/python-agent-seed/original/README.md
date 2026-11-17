# Public Python Agent Seed Pack

This ZIP is a first-run seed package for an agentic coding AI focused on modern Python development.
It does **not** include copied third-party books, courseware, or complete documentation dumps. Instead it includes:

1. A curated public-source manifest with URLs, priorities, licensing notes, and retrieval policies.
2. Original agent instruction files for Python 3.12.7-style coding behavior.
3. Original code examples that demonstrate good and bad Python patterns.
4. Starter eval tasks for testing whether your agent can write, repair, type, secure, and test Python code.
5. Ingestion templates so you can load public material into your retrieval system cleanly.

## Why this pack is link-first

Public does not automatically mean unrestricted. Official docs, university courses, textbooks, GitHub repos, Stack Overflow answers, and papers can all have different license conditions. For a first test run, this pack gives your agent enough original material to practice on and gives your ingestion pipeline a high-quality source roadmap.

## Recommended first ingestion order

1. `01_agent_seed/agent_operating_spec.md`
2. `01_agent_seed/python_3127_coding_doctrine.md`
3. `02_source_catalog/source_manifest.json`
4. `03_ingestion_templates/chunking_policy.md`
5. `04_examples/good/`
6. `04_examples/bad/`
7. `04_examples/refactors/`
8. `05_evals/`

## Recommended retrieval source order

Use the URLs in `02_source_catalog/source_manifest.json` in this order:

1. Official Python 3.12 documentation.
2. PEPs: PEP 8, PEP 257, PEP 484, PEP 695.
3. Python Packaging User Guide and PyPA sample project.
4. Tool docs: pytest, unittest, Ruff, mypy, Pyright, Bandit, coverage.py.
5. Security guidance: OpenSSF Secure Coding Guide for Python and OWASP Cheat Sheet Series.
6. Formal education: MIT OCW, CS50P, Google's Python Class, Think Python, Automate the Boring Stuff.
7. Research papers and benchmarks: HumanEval, ReAct, Reflexion, SWE-bench, SWE-agent, Agentless, Self-Refine, CodeT5.

## Smoke test

From inside this folder, run:

```bash
python scripts/check_pack_integrity.py
python scripts/run_example_tests.py
```

The second command uses `unittest` and standard library only. It does not require pytest, Ruff, or mypy.

## License note

Files in this seed pack are original generated starter material for your first test run. The public-source documents referenced in the manifest are **not** bundled. Check and preserve each upstream source license before copying, fine-tuning on, redistributing, or using it commercially.
