# Offline Local Assistant Settings Validator

Extract the source ZIP and open a terminal in the extracted folder. The release was qualified on Windows and Ubuntu x64 with Python **3.12.16** and **3.15.2**. The tool uses Python's standard library.

## Check a fictional settings file

```
python local_assistant_settings.py --input examples/settings.json
```

Expect normalized JSON on standard output. The example's temperature becomes 2.0, its main context window becomes 4,096, and its tool-round limit becomes 30. The IPv6 loopback URL loses its trailing slash, and the owner and main model labels lose surrounding whitespace.

## Input and output

Pass a UTF-8 JSON object of at most 2,000,000 bytes. Omitted settings use the package defaults. The loopback endpoint can use localhost, 127.0.0.1, or [::1] over HTTP, with an optional valid port and path. The validator rejects credentials, query strings, fragments, and malformed addresses or ports. The check reads the URL as text.

| Setting | Normalized range |
| --- | --- |
| Temperature | 0.0–2.0 |
| Main context window | 4,096–131,072 |
| Fast context window | 2,048–16,384 |
| Tool rounds | 1–30 |
| Output tokens | 128–8,192 |
| History messages | 8–100 |

Unknown reasoning values fall back to auto. Unknown approval-mode values fall back to ask. The settings version normalizes to 3. Model and owner defaults are fictional. The CLI prints settings and leaves the input file untouched. It returns 0 on success and 2 on invalid or unreadable input.

Each qualification profile runs the two original tests, the adapted owner-name assertion, and six CLI check groups. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-assistant-settings-validator-v0.1.0/VALIDATION.json).
