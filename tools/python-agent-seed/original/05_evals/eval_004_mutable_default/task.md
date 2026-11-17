# Eval 004: Mutable default repair

## Task

Fix `starter/tagger.py` so that tags are not shared across calls.

## Requirements

- Keep the public function name `add_tag`.
- Preserve support for passing an existing list of tags.
- Do not mutate the caller's list unless the task is explicitly changed to request mutation.
- Add useful type annotations.
