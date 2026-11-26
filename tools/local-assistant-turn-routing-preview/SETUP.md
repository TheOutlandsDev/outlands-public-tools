# Offline Local Assistant Turn Routing Preview

Extract the source ZIP and open a terminal in the extracted folder. The release was qualified on Windows and Ubuntu x64 with Python **3.12.16** and **3.15.2**. It uses only the standard library.

## Preview three fictional prompts

```text
python turn_routing_preview.py --input examples/fast-chat.json
python turn_routing_preview.py --input examples/workspace.json
python turn_routing_preview.py --input examples/operations.json
```

| Example | Route | Model label | Reasoning | Operations program |
| --- | --- | --- | --- | --- |
| Greeting | `fast_chat` | `fictional-fast` | `false` | `null` |
| Python workspace request | `workspace` | `fictional-main` | `medium` | `null` |
| Rust server status request | `operations` | `fictional-main` | `low` | `rust` |

## Input and output

Use a UTF-8 JSON file of at most 2,000,000 bytes. Include the following fields.

- `user_text` contains the saved prompt as a string.
- `main_model` and `fast_model` are string labels. An empty `fast_model` disables fast chat.
- `fast_routing` is a JSON boolean. Set it to `false` to disable fast chat.
- `main_context_window` and `fast_context_window` are positive integers.
- `configured_reasoning` is a string. Use `auto` for the route's default reasoning setting.
- `context_hint` is optional and defaults to an empty string. The router uses its last 1,000 characters for route matching.

The JSON report includes `kind`, `label`, `model`, `reasoning`, `tool_names`, `context_window`, and `operations_program`. When multiple routes qualify, operations takes precedence over workspace, then fast chat. Main chat is the fallback. For an operations route, `operations_program` is inferred from the prompt and reports `all` when zero or multiple programs match. For other routes it is `null`.

The model and tool names are informational labels. The preview reads the saved input and prints the routing decision as JSON. It exits with code `0` for a preview or `2` for invalid or unreadable input, including duplicate or unknown JSON fields.

[Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-assistant-turn-routing-preview-v0.1.0/VALIDATION.json).
