# Chunking Policy

## Target chunk size

- Normal prose: 500 to 1,200 tokens.
- Dense API reference: 300 to 900 tokens.
- Code examples: keep full example and explanation together when possible.

## Overlap

Use 75 to 150 tokens of overlap when splitting long sections.

## Preserve with every chunk

- Source ID.
- Source title.
- URL.
- Version, if applicable.
- Heading path.
- License note.
- Retrieval date.
- Priority.
- Topics.

## Avoid ingesting

- Navigation menus.
- Cookie banners.
- Sidebar text.
- Repeated footer text.
- Search index text.
- Unlicensed copied code.
- Course solution repositories.

## Special handling

### Python docs

Tag all Python docs with `python_version: "3.12"`. Do not mix latest Python docs into this corpus unless they are marked separately.

### PEPs

Preserve PEP number and status. Some PEPs are historical context; current docs may supersede details.

### Research papers

Chunk abstract, method, evaluation setup, limitations, and agent-design implications separately. Do not train the agent to imitate paper prose.

### Code examples

Pair each example with a note explaining why the code is good or bad.
