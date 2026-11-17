# Eval 001: Pathlib JSON Loader

## Task

Fix `starter/json_loader.py` so that it:

- Uses `pathlib.Path`.
- Reads UTF-8 text.
- Parses JSON.
- Requires the top-level JSON value to be an object.
- Raises `JsonLoaderError` with useful context for unreadable files, invalid JSON, or wrong top-level type.
- Keeps the public function name `load_json_object`.

## Constraints

- Use only the Python standard library.
- Do not use broad `except Exception`.
- Do not change the tests.
