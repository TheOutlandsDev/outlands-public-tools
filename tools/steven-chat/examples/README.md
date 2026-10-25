# Fictional examples

`session.json` documents the versioned conversation format. Every message is
invented. Its `example-local:tiny` model name is a placeholder, not a model
recommendation or downloadable artifact. Do not send it to a backend as though
it were an installed model. Real sessions must use the exact selected local
model identifier and satisfy the same validation rules.

Run the no-network demonstration from the tool directory:

```text
python -m steven --demo
```

For actual chat, prepare a separate trusted Ollama server with cloud features
disabled and a separately reviewed/installed model. Use `models --connect` to
inspect the local list, then substitute the chosen model name into the README's
commands. The client never downloads the placeholder or any other model.

Keep personal prompts, responses, backend logs and session exports outside this
folder and outside GitHub. The supplied example's public status does not make
future real transcripts safe to publish.
