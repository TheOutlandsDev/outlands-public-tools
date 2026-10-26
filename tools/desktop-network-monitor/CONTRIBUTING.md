# Contributions and suggestions

Use [the app forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)
for bug reports, usability improvements, format proposals and fictional rule
examples. Include source commit, OS/Python/Tk/dependency versions, steps and
expected results. Distinguish demo, replay, injected failure, offline decoding
and native live acceptance.

Do not post real IPs, interface names, packet captures, payloads, logs, CSVs,
API keys, customer data or unreviewed reports. Relative traffic structure can
still identify a session. Do not infer malware from a port, size or pulse count.

Preserve MIT source notices and separate optional dependency/driver notices.
Do not bundle a Scapy/capture environment as MIT-only. Tests must use generated
fixtures and mocked reputation transport; no live capture, traffic injection,
automatic external lookups, credential discovery or driver install is permitted
as a default test. Keep capture process termination scoped to owned children.
