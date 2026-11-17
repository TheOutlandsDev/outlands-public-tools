# Source Manifest Index

## History and License, Python 3.12 Documentation

- ID: `python-docs-license`
- URL: https://docs.python.org/3.12/license.html
- Type: license
- Authority: Python Software Foundation
- Priority: 1
- Topics: license, psf, 0bsd
- License note: Defines PSF-2.0 documentation license and 0BSD treatment for documentation code examples.
- Retrieval policy: Keep as legal metadata; do not train behavior from license text beyond source compliance.
- Recommended use: Source license record for Python docs.

## Packaging Python Projects - Python Packaging User Guide

- ID: `pypa-packaging-projects`
- URL: https://packaging.python.org/en/latest/tutorials/packaging-projects/
- Type: official_documentation
- Authority: Python Packaging Authority
- Priority: 1
- Topics: packaging, project-layout, build, publish
- License note: PyPA docs are public; preserve source/license metadata from upstream repository.
- Retrieval policy: Use for packaging tutorial tasks; avoid treating tutorial choices as mandatory enterprise standards.
- Recommended use: Teach packaging workflow and project skeletons.

## Writing your pyproject.toml - Python Packaging User Guide

- ID: `pypa-pyproject`
- URL: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Type: official_documentation
- Authority: Python Packaging Authority
- Priority: 1
- Topics: packaging, pyproject.toml, build-system, metadata
- License note: PyPA docs are public; preserve source/license metadata from upstream repository.
- Retrieval policy: Ingest sections on build-system, project metadata, and tool config.
- Recommended use: Teach modern project configuration.

## Python 3.12 Documentation

- ID: `python-312-docs-root`
- URL: https://docs.python.org/3.12/
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: python-3.12, language, standard-library, runtime
- License note: Python docs are under the PSF License Version 2; examples/code are dual licensed under PSF-2.0 and 0BSD for Python 3.8.6+.
- Retrieval policy: Prefer link/RAG ingestion. Copy only with attribution and license preservation.
- Recommended use: Primary source for Python 3.12 syntax, semantics, and standard library behavior.

## Python Language Reference, Python 3.12

- ID: `python-312-language-reference`
- URL: https://docs.python.org/3.12/reference/
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: syntax, data-model, execution-model, expressions, compound-statements
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Ingest as high-authority reference; do not summarize away formal definitions.
- Recommended use: Use for exact language semantics and edge cases.

## Python Standard Library, Python 3.12

- ID: `python-312-library-reference`
- URL: https://docs.python.org/3.12/library/
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: standard-library, pathlib, typing, logging, subprocess, unittest, asyncio
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Start with selected modules: pathlib, dataclasses, typing, logging, argparse, subprocess, json, csv, unittest, asyncio.
- Recommended use: Primary source for standard library APIs.

## Python Tutorial, Python 3.12

- ID: `python-312-tutorial`
- URL: https://docs.python.org/3.12/tutorial/
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: python-basics, control-flow, data-structures, modules, exceptions, classes
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Chunk by section heading; preserve heading path and version metadata.
- Recommended use: Teach baseline Python concepts to the agent.

## What's New In Python 3.12

- ID: `python-312-whats-new`
- URL: https://docs.python.org/3.12/whatsnew/3.12.html
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: python-3.12, new-features, deprecations, distutils-removal, typing
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Ingest as version-specific diff. Mark as Python 3.12 only.
- Recommended use: Teach version-specific changes that affect generated code.

## Python Security Considerations

- ID: `python-security-considerations`
- URL: https://docs.python.org/3.12/library/security_warnings.html
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: security, pickle, subprocess, secrets, tempfile, zipfile
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Use as hard safety source for modules like pickle, shelve, subprocess, tempfile, zipfile, xml.
- Recommended use: Teach unsafe standard-library patterns to avoid.

## typing - Support for type hints

- ID: `typing-docs`
- URL: https://docs.python.org/3.12/library/typing.html
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: typing, protocol, typed-dict, generics, literal, self
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Ingest as primary typing API reference for Python 3.12.
- Recommended use: Core source for typed Python generation.

## unittest - Unit testing framework

- ID: `unittest-docs`
- URL: https://docs.python.org/3.12/library/unittest.html
- Type: official_documentation
- Authority: Python Software Foundation
- Priority: 1
- Topics: testing, unittest, standard-library
- License note: PSF-2.0 docs; example code PSF-2.0/0BSD.
- Retrieval policy: Ingest as fallback when project uses stdlib testing.
- Recommended use: Teach stdlib testing.

## PEP 257 - Docstring Conventions

- ID: `pep-257`
- URL: https://peps.python.org/pep-0257/
- Type: pep
- Authority: Python Software Foundation
- Priority: 1
- Topics: docstrings, documentation, public-api
- License note: Public PEP source; preserve attribution and URL.
- Retrieval policy: Ingest conventions for public modules, classes, and functions.
- Recommended use: Teach docstring style.

## PEP 484 - Type Hints

- ID: `pep-484`
- URL: https://peps.python.org/pep-0484/
- Type: pep
- Authority: Python Software Foundation
- Priority: 1
- Topics: typing, type-hints, static-analysis
- License note: Public PEP source; preserve attribution and URL.
- Retrieval policy: Use together with current typing docs; do not treat old examples as exhaustive.
- Recommended use: Teach historical basis for Python type hints.

## PEP 695 - Type Parameter Syntax

- ID: `pep-695`
- URL: https://peps.python.org/pep-0695/
- Type: pep
- Authority: Python Software Foundation
- Priority: 1
- Topics: python-3.12, typing, generics
- License note: Public PEP source; preserve attribution and URL.
- Retrieval policy: Mark as Python 3.12+ syntax; avoid using if target project disallows it.
- Recommended use: Teach modern generic class/function syntax.

## PEP 8 - Style Guide for Python Code

- ID: `pep-8`
- URL: https://peps.python.org/pep-0008/
- Type: pep
- Authority: Python Software Foundation
- Priority: 1
- Topics: style, naming, imports, readability
- License note: Python PEPs are publicly hosted; preserve attribution and source URL.
- Retrieval policy: Ingest key recommendations; project local style overrides PEP 8.
- Recommended use: Default code style baseline.

## OpenSSF Secure Coding Guide for Python

- ID: `openssf-python-secure-coding`
- URL: https://best.openssf.org/Secure-Coding-Guide-for-Python/
- Type: security_guidance
- Authority: OpenSSF
- Priority: 1
- Topics: secure-coding, python, logging, neutralization, exceptions, cryptography
- License note: OpenSSF page states docs are CC-BY-4.0 and code is MIT; preserve attribution/license.
- Retrieval policy: High-priority security guidance; chunk rules and examples together.
- Recommended use: Teach secure Python defaults.

## OWASP Cheat Sheet Series

- ID: `owasp-cheat-sheet-series`
- URL: https://cheatsheetseries.owasp.org/
- Type: security_guidance
- Authority: OWASP
- Priority: 1
- Topics: application-security, input-validation, logging, secrets, ai-security
- License note: Public OWASP project; preserve upstream license and attribution if copied.
- Retrieval policy: Use selected sheets: Input Validation, Logging, Secrets Management, OS Command Injection, Secure Coding with AI, LLM Prompt Injection.
- Recommended use: Teach application security guardrails.

## Mypy documentation

- ID: `mypy-docs`
- URL: https://mypy.readthedocs.io/en/stable/
- Type: tool_documentation
- Authority: Mypy project
- Priority: 1
- Topics: typing, mypy, static-analysis
- License note: Public project docs; preserve upstream license and attribution if copied.
- Retrieval policy: Ingest getting started, config, common issues, strict optional behavior.
- Recommended use: Teach type checking workflow.

## pytest documentation

- ID: `pytest-docs`
- URL: https://docs.pytest.org/en/stable/
- Type: tool_documentation
- Authority: pytest project
- Priority: 1
- Topics: testing, pytest, fixtures, parametrize
- License note: Public project docs; preserve upstream license and attribution if copied.
- Retrieval policy: Ingest getting started, fixtures, parametrization, tmp_path, monkeypatch.
- Recommended use: Teach tests-first and regression test generation.

## Ruff documentation

- ID: `ruff-docs`
- URL: https://docs.astral.sh/ruff/
- Type: tool_documentation
- Authority: Astral
- Priority: 1
- Topics: linting, formatting, ruff, quality
- License note: Public project docs; preserve upstream license and attribution if copied.
- Retrieval policy: Ingest command usage, pyproject config, rule families, formatter docs.
- Recommended use: Teach fast lint/format workflow.

## OpenAI HumanEval GitHub repository

- ID: `human-eval-github`
- URL: https://github.com/openai/human-eval
- Type: benchmark_code
- Authority: OpenAI
- Priority: 2
- Topics: benchmark, code-generation, python
- License note: Repository indicates MIT license.
- Retrieval policy: Use as optional benchmark source; keep separate from training to avoid contamination.
- Recommended use: Optional evaluation harness reference.

## SWE-bench GitHub repository

- ID: `swe-bench-github`
- URL: https://github.com/SWE-bench/SWE-bench
- Type: benchmark_code
- Authority: SWE-bench project
- Priority: 2
- Topics: benchmark, software-engineering, github-issues
- License note: Check repository license and dataset terms before copying or training.
- Retrieval policy: Use as external benchmark, not as initial training corpus.
- Recommended use: Later-stage coding-agent evaluation.

## Google's Python Class

- ID: `google-python-class`
- URL: https://developers.google.com/edu/python/
- Type: formal_education
- Authority: Google for Developers
- Priority: 2
- Topics: formal-education, python-exercises, regex, files
- License note: Check Google site terms and any exercise archive license before copying content.
- Retrieval policy: Use as link/reference; ingest only after license review.
- Recommended use: Supplementary practice exercise ideas.

## CS50's Introduction to Programming with Python

- ID: `harvard-cs50p`
- URL: https://cs50.harvard.edu/python/
- Type: formal_education
- Authority: Harvard CS50
- Priority: 2
- Topics: formal-education, intro-python, testing, debugging
- License note: Course license page states CC BY-NC-SA 4.0; non-commercial/share-alike restrictions apply.
- Retrieval policy: Use as educational roadmap/link source; do not copy problem sets/solutions into a commercial corpus without license review.
- Recommended use: Curriculum sequencing and beginner exercise inspiration.

## MIT OCW 6.100L Introduction to CS and Programming Using Python

- ID: `mit-6-100l`
- URL: https://ocw.mit.edu/courses/6-100l-introduction-to-cs-and-programming-using-python-fall-2022/
- Type: formal_education
- Authority: MIT OpenCourseWare
- Priority: 2
- Topics: formal-education, intro-python, computer-science
- License note: MIT OCW content generally uses CC BY-NC-SA 4.0 unless otherwise marked; non-commercial/share-alike restrictions apply.
- Retrieval policy: Use as educational roadmap/link source; do not copy into commercial training corpus without license review.
- Recommended use: Curriculum sequencing and exercise inspiration.

## PyPA sampleproject

- ID: `pypa-sampleproject`
- URL: https://github.com/pypa/sampleproject
- Type: public_code_example
- Authority: Python Packaging Authority
- Priority: 2
- Topics: packaging, pyproject.toml, sample-project
- License note: Public repository; check repository LICENSE.txt before copying files.
- Retrieval policy: Use as packaging example only; the README says it is not a full best-practices guide.
- Recommended use: Reference minimal packaging structure.

## Agentless: Demystifying LLM-based Software Engineering Agents

- ID: `agentless-paper`
- URL: https://arxiv.org/abs/2407.01489
- Type: research_paper
- Authority: arXiv / Xia et al.
- Priority: 2
- Topics: software-engineering, agents, localization, repair, validation
- License note: Paper hosted by arXiv; check code repo license separately.
- Retrieval policy: Use as a baseline for simple localization-repair-validation workflows.
- Recommended use: Counterweight against overly complex agent loops.

## Evaluating Large Language Models Trained on Code

- ID: `human-eval-paper`
- URL: https://arxiv.org/abs/2107.03374
- Type: research_paper
- Authority: arXiv / OpenAI et al.
- Priority: 2
- Topics: code-generation, evaluation, humaneval, pass-at-k
- License note: Paper hosted by arXiv; HumanEval harness repository uses MIT license. Check dataset terms before redistributing.
- Retrieval policy: Use for eval design concepts, not as sole benchmark due to contamination concerns.
- Recommended use: Understand functional correctness evaluation for generated code.

## ReAct: Synergizing Reasoning and Acting in Language Models

- ID: `react-paper`
- URL: https://arxiv.org/abs/2210.03629
- Type: research_paper
- Authority: arXiv / Yao et al.
- Priority: 2
- Topics: agents, tool-use, reasoning, acting
- License note: Paper hosted by arXiv; check arXiv license metadata before copying full text.
- Retrieval policy: Use as agent design concept: interleave reasoning, action, observation.
- Recommended use: Design source for tool-using coding agents.

## Reflexion: Language Agents with Verbal Reinforcement Learning

- ID: `reflexion-paper`
- URL: https://arxiv.org/abs/2303.11366
- Type: research_paper
- Authority: arXiv / Shinn et al.
- Priority: 2
- Topics: agents, reflection, verbal-feedback, coding
- License note: Paper hosted by arXiv; repo code is separate and should be license-checked.
- Retrieval policy: Use for eval feedback and self-reflection patterns; do not let agent self-approve regulated changes.
- Recommended use: Design source for feedback loops.

## SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering

- ID: `swe-agent-paper`
- URL: https://arxiv.org/abs/2405.15793
- Type: research_paper
- Authority: arXiv / Yang et al.
- Priority: 2
- Topics: agents, software-engineering, agent-computer-interface, tool-use
- License note: Paper hosted by arXiv; check code repo license separately.
- Retrieval policy: Use for tool/interface design, especially file editing, navigation, and test execution.
- Recommended use: Design agent tool protocol and feedback surfaces.

## SWE-bench: Can Language Models Resolve Real-World GitHub Issues?

- ID: `swe-bench-paper`
- URL: https://arxiv.org/abs/2310.06770
- Type: research_paper
- Authority: arXiv / Princeton and Stanford researchers
- Priority: 2
- Topics: software-engineering, benchmark, github-issues, patch-generation
- License note: Paper hosted by arXiv; benchmark repository/data have their own license requirements.
- Retrieval policy: Use for software engineering eval design and issue-to-patch workflows.
- Recommended use: Design realistic coding-agent tests.

## Bandit documentation

- ID: `bandit-docs`
- URL: https://bandit.readthedocs.io/en/latest/
- Type: security_tool_documentation
- Authority: PyCQA / Bandit project
- Priority: 2
- Topics: security, static-analysis, bandit
- License note: Public project docs; preserve upstream license and attribution if copied.
- Retrieval policy: Ingest basic usage and common rule explanations.
- Recommended use: Teach Python security linting workflow.

## Coverage.py documentation

- ID: `coverage-docs`
- URL: https://coverage.readthedocs.io/
- Type: tool_documentation
- Authority: Coverage.py project
- Priority: 2
- Topics: testing, coverage, quality
- License note: Public project docs; preserve upstream license and attribution if copied.
- Retrieval policy: Ingest basic usage and reporting only for first run.
- Recommended use: Teach measuring test coverage.

## Pyright documentation

- ID: `pyright-docs`
- URL: https://microsoft.github.io/pyright/
- Type: tool_documentation
- Authority: Microsoft / Pyright project
- Priority: 2
- Topics: typing, pyright, static-analysis
- License note: Public project docs; preserve upstream license and attribution if copied.
- Retrieval policy: Ingest only if your agent environment uses Pyright or Pylance.
- Recommended use: Alternative type checker reference.

## Automate the Boring Stuff with Python

- ID: `automate-the-boring-stuff`
- URL: https://automatetheboringstuff.com/
- Type: open_textbook
- Authority: Al Sweigart / No Starch Press
- Priority: 3
- Topics: automation, files, web, excel, practical-python
- License note: Website says the book is free to read under a Creative Commons license; verify edition-specific terms before copying.
- Retrieval policy: Use as link/reference; include license and attribution if copied.
- Recommended use: Practical automation examples after core docs.

## Think Python, 2nd edition

- ID: `think-python-2e`
- URL: https://greenteapress.com/wp/think-python-2e/
- Type: open_textbook
- Authority: Allen B. Downey / Green Tea Press
- Priority: 3
- Topics: intro-python, computer-science, recursion, oop
- License note: CC BY-NC 3.0 according to Green Tea Press page; non-commercial restriction applies.
- Retrieval policy: Use as link/reference; do not mix into commercial corpus without license review.
- Recommended use: Conceptual teaching and exercises.

## CodeT5: Identifier-aware Unified Pre-trained Encoder-Decoder Models for Code Understanding and Generation

- ID: `codet5-paper`
- URL: https://arxiv.org/abs/2109.00859
- Type: research_paper
- Authority: arXiv / Salesforce Research
- Priority: 3
- Topics: code-models, pretraining, identifiers, code-generation
- License note: Paper hosted by arXiv; code/model licenses should be checked separately.
- Retrieval policy: Use as background on code model pretraining and identifier-aware representation.
- Recommended use: Research background for code understanding models.

## Self-Refine: Iterative Refinement with Self-Feedback

- ID: `self-refine-paper`
- URL: https://arxiv.org/abs/2303.17651
- Type: research_paper
- Authority: arXiv / Madaan et al.
- Priority: 3
- Topics: self-feedback, iterative-refinement, agents
- License note: Paper hosted by arXiv; GitHub repo has separate Apache-2.0 license.
- Retrieval policy: Use for iterative improvement patterns; require external tests and objective feedback.
- Recommended use: Design review/refine loops.
