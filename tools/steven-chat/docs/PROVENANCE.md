# Provenance and publication scope

The owner identified the local chatbot by both **Stephen** and **Steven**. The
reviewed starting source was a small personal project with two near-duplicate
terminal loops, named `main.py` and `chatbot.py`, plus a project file and ad hoc
installation notes. The loops constructed a Transformers conversational pipeline
with `microsoft/DialoGPT-medium` at import time. No tests, detailed guide or
first-party license file accompanied those selected draft files.

The public release is a freshly authored implementation of that local-chat use
case, with AI assistance. It replaces duplicated model initialization with a
standard-library HTTP client, explicit installed-model selection, bounded context,
strict sessions and an offline demo. The `main.py`, `chatbot.py` and `stephen.py`
entry points retain naming continuity. It is not a wholesale export of the old
project or a retroactive license claim over its virtual environment.

The owner authorized cleanup, testing and public MIT publication in the shared
OUTLANDS Public Tools collection. Owner-reported personal authorship and this
selected-source review are not independent guarantees of exclusive authorship of
unrelated historical material. No attribution or license notice was removed from
the selected original source. The original local project remains unchanged;
original-path/checksum records are retained privately outside this source export.

Only the explicitly reviewed original client, tests, documentation and fictional
examples receive this folder's MIT grant. No old environment, installed package,
model weight, real conversation, account configuration, private absolute path or
historical project metadata is included. No dependency implementation was copied.

Ollama's documented HTTP interface informed this original client. Ollama is a
separate optional runtime with its own MIT source license; Python and each model
have their own terms. No model license was inferred from an API response or name.
See THIRD-PARTY-NOTICES.txt and DEPENDENCIES.json for the scoped dependency record.

Generated fixtures establish the selected client behavior only. No real Ollama
installation/model inference was performed for this release. The client cannot
prove backend offline behavior, model provenance, answer quality or hardware fit.
