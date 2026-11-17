# Public Documentation Sources

Use `source_manifest.json` as the machine-readable source of truth. This file explains why these sources are useful.

## Highest priority

- Python 3.12 documentation: language, tutorial, library reference, security warnings, typing, unittest.
- Python PEPs: style, docstrings, type hints, Python 3.12 type parameter syntax.
- Python Packaging User Guide: pyproject.toml, packaging projects, modern packaging workflow.

## Tooling documentation

- pytest: fixtures, parametrization, tmp_path, monkeypatch, test discovery.
- Ruff: linting, formatting, rule selection, pyproject configuration.
- mypy/Pyright: static type checking behavior and config.
- Bandit: Python security linting.
- coverage.py: measuring test coverage.

## Security documentation

- OpenSSF Secure Coding Guide for Python.
- OWASP Cheat Sheet Series.
- Python security considerations.

## License handling

Do not mix all documents into a single copied training corpus unless license review approves it. For a safe first run, use URLs and metadata, then retrieve chunks dynamically.
