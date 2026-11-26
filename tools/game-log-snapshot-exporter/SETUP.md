# Offline Game Log Snapshot Exporter

Use Python **3.12.16** or **3.15.2** on Windows or Ubuntu x64. Extract the source ZIP. The exporter requires only the standard library and does not connect to a server. Use saved log copies in a folder you control.

## Export a fictional log

From the extracted folder, run this command on Windows or Ubuntu.

```
python game_log_snapshot_exporter.py rust --source-root examples --pattern rust.log --at 2020-01-02T03:00:00Z --output-root snapshots
```

The JSON receipt includes the new file path and digest. The snapshot contains four events from the fictional Rust log. Omit the output option to send the snapshot itself to standard output. File output requires a filesystem that supports hard links, such as NTFS or ext4. Existing snapshots are refused. The output directory must be separate from the input tree.

Download and extract [Verifier and Replay v0.1.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/game-telemetry-snapshot-verifier-replay-v0.1.0). Run the verifier using the snapshot path printed by the exporter.

```
python path/to/telemetry_snapshot_replay.py verify path/to/saved-snapshot.json
```

Expect a JSON report with an ok value of true, the Rust profile, four events, and the same SHA-256 digest.

## Inputs and output

- Choose rust, dayz, main_spt, modern_warfare, or zomboid. Quote wildcard patterns and repeat the pattern option to add more patterns. Accepted suffixes are .log, .rpt, and .txt. Sensitive-looking filenames and linked files or directories are skipped. Absolute patterns and parent traversal are refused.
- The CLI reads the newest three matching files, up to the last 512 KiB of each. It drops the first line when the read starts partway through a file. The snapshot is limited to 10,000 records and 2,000,000 serialized bytes. For a smaller export, select fewer files or use smaller saved copies.
- The exporter keeps supported events and allowed context fields, replaces source filenames with numbered labels, and represents player identifiers with deterministic pseudonyms. The snapshot still contains selected game context, source modification times, and hashes of the bytes read. Review it before sharing. The original filters look for selected patterns and the pseudonyms can link activity across exports, so use fictional source logs for public examples.
- The fixed timestamp option sets the snapshot's generation time. Source modification times still participate in the checksum.
- The digest detects changes to the snapshot contents. It provides no signature or proof of authorship.

The release qualification retains five original export tests using fictional log lines. It also checks the copied CLI and runs the pinned public verifier against output from all five game profiles. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/game-log-snapshot-exporter-v0.1.0/VALIDATION.json).
