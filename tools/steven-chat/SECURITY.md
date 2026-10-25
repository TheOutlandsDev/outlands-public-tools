# Security and privacy boundaries

Steven sends prompts and retained context to the explicitly selected loopback
server only after `--connect`. Loopback validation, no environment proxies and no
redirects limit this client's destination. They do not establish that an Ollama
server, container or custom forwarding service is trustworthy or stays offline.
Disable cloud features in the server and review its configuration separately.

Model output is text. The client provides no shell, browser, tool-calling or
file-execution facility. Control characters are escaped before terminal output.
Bounds and schema checks are defensive measures, not a hostile-process sandbox.
Use stable, trusted directories; path checks cannot eliminate filesystem races
or protect against a local administrator or compromised account.

Conversations may contain sensitive information. Saving is explicit and creates
a fresh clear-text file. POSIX mode is owner-only; Windows ACLs are inherited.
There is no encryption, anonymity, secure erase or removal of terminal/server
history. Do not put transcripts, private session fixtures, account credentials,
private paths or unredacted logs in GitHub. The public examples are fictional.

For a suspected defect, prepare a minimal fictional reproduction. Do not post
active credentials, real conversations or exploitation details exposing another
person's data. Use GitHub's private vulnerability reporting if the repository
offers it; otherwise contact the maintainer through a channel they explicitly
provide. Do not assume that creating an ordinary issue is private.
