# Fictional examples

From the module directory, choose a new absolute directory whose parent already
exists:

```text
python -B examples/generate.py --output ABSOLUTE_NEW_DEMO_DIRECTORY
```

Replace the placeholder before running. Outputs remain outside the source
checkout and are not uploaded. Each file is a tiny original byte arrangement
for parser tests, with obvious fake payloads. None can boot a device.

| Generated input | Expected exit | Expected observation |
| --- | --- | --- |
| `boot-v3.img` | 0 | Header, kernel and ramdisk declared within a 12288-byte layout. |
| `boot-v4.img` | 0 | Adds a 9-byte signature declaration in a 16384-byte layout; signature is not verified. |
| `vendor-v3.img` | 0 | Header, 12-byte ramdisk and 5-byte DTB declarations. |
| `vendor-v4.img` | 0 | Two 108-byte table entries, fragment extents 0..5 and 5..12, 6-byte bootconfig declaration. |
| `truncated-vendor.img` | 1 | Table/bootconfig sections exceed the file; table is not read. |
| `unsupported-legacy.img` | 1 | Header version 2 is unsupported and no component layout is inferred. |

Pass one generated absolute input path to `boot_inspector.py --image`, with a
different new absolute `--output` directory for each run. Review the JSON and
static HTML. Neither report includes names, command lines, board IDs or input
paths; header hashes may still identify a build. Do not attach real inputs or
unreviewed reports to public issues.

The generator refuses an existing output directory. Reusing output paths is
deliberately not an overwrite workflow; choose fresh paths for repeated runs.
