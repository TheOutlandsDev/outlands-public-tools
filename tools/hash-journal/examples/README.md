# Fictional journal example

`two-record.jsonl` is original generated data containing two fictional build
events. It is not historical project evidence. Its head is:

```text
ec91f00284e1d0faccd7f3301ae23ae7af1c8eed6121cab890dd1648d9f33d36
```

The file and head were independently generated with Python's `hashlib.sha256`
using the exact [version 1 formula](../docs/FORMAT.md). The C# fixture harness
reads the public example and checks its trusted head and count.

After the documented build, select the example through its **absolute** path:

```text
dotnet APP_DLL verify --input ABSOLUTE_SOURCE_FOLDER/examples/two-record.jsonl --expected-head ec91f00284e1d0faccd7f3301ae23ae7af1c8eed6121cab890dd1648d9f33d36 --expected-count 2
```

Replace `APP_DLL` and `ABSOLUTE_SOURCE_FOLDER` with your actual paths. This
command reads the fictional file and writes JSON metadata to the terminal;
it creates no file. A local copy with a modified first text should fail its
stored hash. A complete-record prefix can pass without an expected head/count,
but the independently expected two-record head catches that removed tail.

To create your own demonstration versions, use the README's `create`/`append`
commands with new filenames in an existing external private workspace. Do not
overwrite the checked-in fixture or place actual event logs in the source tree.
The demo command's JSON display is not a JSONL file to use as a journal.
