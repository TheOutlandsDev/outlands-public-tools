# Security and private input handling

This tool accepts explicit stable regular local files and bounds metadata reads,
chunk count, output declarations and report bytes. It never reconstructs, mounts,
flashes or executes an input and does not invoke external programs or networks.
Its checks are limited observations, not a security certification or assurance
that another tool can safely process the same file.

Work in directories you control. Link/reparse refusal and before/after file
identity checks detect ordinary races but do not form a filesystem sandbox or
atomic snapshot against a malicious concurrent writer. An incomplete run may
leave a partially created fresh output directory; inspect it before reuse and
choose a new directory for the next run.

Local paths and payloads are omitted from reports. Metadata lengths/layouts and
region hashes can still identify a file. Do not publish raw firmware or reports
without reviewing privacy and redistribution rights. Report hashes are unsigned.

For a security concern use the repository's security reporting route described
in its root security policy. A public issue may discuss a minimized invented
reproduction only; do not disclose secrets, vendor payloads or identifying data.
