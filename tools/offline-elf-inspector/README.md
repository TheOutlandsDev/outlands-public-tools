# OUTLANDS | Offline ELF Dependency Inspector

Inspect the declared library dependencies of local Linux/Android ELF files
without running them. Find metadata candidates in folders you select, distinguish
ambiguous providers and architecture mismatches, and export an offline HTML/JSON
report. Original code, tests, documentation and generated examples are
[MIT licensed](LICENSE).

This tool comes from the owner's local phone dependency-analysis workflow. The
public version is a fresh portable implementation: **Python 3.12 or 3.13, standard
library only**. It reads ELF metadata directly on Windows or Linux. No `pip`,
`readelf`, WSL, Android SDK, connected phone, root access or firmware download is
required. No inspected binary is loaded, imported, executed, copied into a report,
repaired or uploaded. There is no device/build/flash command.

## Start here

1. Download or clone [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools).
2. Open a terminal in `tools/offline-elf-inspector`.
3. Confirm `python --version` is 3.12 or 3.13 (`python3` on systems using that name).
4. Start with the generated example below. It needs no actual software or firmware.

```text
python -B elf_inspector.py --help
python -B examples/make_demo.py --destination ../elf-demo
python -B elf_inspector.py --file ../elf-demo/app/demo.elf --root ../elf-demo/lib --output ../elf-report
```

Expect exit **2**, meaning review findings were reported. Open
`../elf-report/index.html` directly in your browser. It uses no JavaScript,
external assets, server or network connection. This example deliberately includes:

| Declared dependency | Expected finding |
| --- | --- |
| `libdemo.so` | One metadata candidate whose filename is `libdemo-real.so` and SONAME is `libdemo.so`. |
| `libchoice.so` | Two matching providers; no arbitrary winner is chosen. |
| `libabsent.so` | Unresolved in the supplied inputs. |
| `libwrong.so` | A matching name with a different ELF class/machine. |

The unique branch follows `libdemo.so` to `libleaf.so` and back, demonstrating
cycle-safe traversal. Ambiguous branches are not followed. The generated files
contain authored metadata and padding, **no executable machine code**. They are
not loader-valid test programs and must not be executed. A text file is ignored.
See the [worked examples](examples/README.md), including a clean exit-0 example.
Use NEW demo and output folders when repeating commands.

From the collection root, the corresponding entry point is:

```text
python -B tools/offline-elf-inspector/elf_inspector.py --help
```

## Inspect your own files

Replace the sample paths with your own trusted local paths. Search roots must be
existing, ordinary directories and must be disjoint (no nested or duplicate roots).
The output must be a NEW directory with an existing parent, outside every search root.

```text
python -B elf_inspector.py --file /local/project/app --root /local/project/libs --root /local/sysroot/usr/lib --output /local/reports/elf-new
```

On Windows, quote paths containing spaces:

```powershell
python -B elf_inspector.py --file 'D:\MyProject\app.elf' --root 'D:\MyProject\libs' --output 'D:\Reports\elf-new'
$LASTEXITCODE
```

Use `--file` repeatedly for up to 32 entry files. With selected files, the graph
starts from those entries and follows only unique metadata candidates. Supplied
root contents are still inventoried to find providers. An entry file does not
automatically cause its parent or siblings to be scanned. If a selected file is
also found under a root, its path is inspected once.

Without `--file`, every supported ELF found within the selected roots becomes an entry:

```text
python -B elf_inspector.py --root /local/sysroot --sha256 --output /local/reports/full-new
```

Files are identified by ELF magic, not their extension. PE/DLL/EXE, Mach-O,
archives, firmware images and non-ELF files are not inspected as ELF. Already
extracted ELF files may be inputs; this tool performs no extraction. An explicitly
selected non-ELF is a coverage issue; unrelated non-ELFs discovered in roots are
counted as ignored.

Omit `--output` to write the complete JSON report to stdout. Prefer `--output`
when saving: shell redirection can overwrite a file before the program runs.
There is no automatic report upload, browser launch, saved configuration or scan
of default system folders.

## Understand candidate resolution

The inspector reads the ELF header, program headers, `PT_DYNAMIC`, file-backed
dynamic string table, `DT_NEEDED`, `DT_SONAME`, `DT_RPATH`, `DT_RUNPATH` and optional
`PT_INTERP`. It supports ELF32/ELF64, little/big endian, and EXEC/DYN types in the
documented subset. Section headers and section names are not needed.

It indexes both each inspected file's basename and its declared SONAME. A dependency
candidate must be a DYN object with the same **class, byte order and machine ID**
as its consumer. Matching is case-sensitive. Search-root order is not loader priority.
Multiple same-architecture providers stay ambiguous, even if their bytes match.
All counts remain visible; at most 16 candidate IDs per edge are displayed.

| Finding | Interpretation |
| --- | --- |
| `unique_metadata_candidate` | Exactly one candidate matches these limited metadata criteria. The graph follows it. |
| `ambiguous_candidates` | More than one compatible metadata provider exists. No winner is selected. |
| `architecture_mismatch` | Matching names exist but differ in class, byte order or machine. |
| `object_type_mismatch` | An architecture-matching name exists, but it is not a DYN object. |
| `unresolved_in_supplied_inputs` | No provider was identified in this inventory. It may exist elsewhere. |
| `path_dependency_not_resolved` | A dependency contains a slash/backslash. Path-based loader behavior is outside this resolver. |

**A unique candidate does not prove that an OS loader will load it.** The report
does not emulate Android linker namespaces, APEX, system caches, environment
variables, root order, symbol versions, relocations, CPU features, full ABI flags,
OSABI compatibility, RPATH/RUNPATH expansion or `dlopen`. Search/interpreter paths
are observed text only. Library-looking runtime strings are not treated as proven
dependencies. Missing supplied inputs and skipped links can leave providers unseen.
The original phone scripts' vendor-first/first-match policy is not used here.

## Outputs and exit codes

A report folder contains exactly four files:

- `index.html`: readable summary, dependency findings, file metadata and coverage issues.
- `report.json`: complete structured result; see the [format reference](docs/FORMAT.md).
- `README.txt`: privacy and interpretation reminder.
- `MANIFEST.json`: lengths and SHA-256 of the three payload files (not itself).

Writes are exclusive and read back for byte equality. Existing output is refused.
Failure/cancellation during output may leave a partial **new** folder for inspection;
retry with a different new name. The manifest is not a signature or a source backup.

| Exit | Meaning |
| --- | --- |
| 0 | `NO_SCOPE_FINDINGS`: no coverage issue or unresolved/ambiguous/incompatible dependency was found within this limited inspection. |
| 2 | `REVIEW_REQUIRED`: findings, malformed/unsupported ELF metadata, truncation, skipped links, unreadable input or limits need review. |
| 1 | Controlled input, output or report-size error. No successful report is promised. |
| 130 | Ctrl+C was received and handled; an output started earlier may be partial. |

Argument-usage errors from Python's argument parser exit 2. A file without a
dynamic segment can have no declared dependencies in this report; that does not
certify static linking or loader validity. An inventory with no supported ELF
files requires review. This is a metadata inspector, not a complete ELF validator.

## Bounds and filesystem limits

| Bound | Default / maximum |
| --- | --- |
| Supplied roots / selected entry files | 8 / 32 |
| Regular files examined (`--max-files`) | 2,000 / configurable to 10,000 |
| Directory entries (`--max-entries`) | 20,000 / configurable to 100,000 |
| Subdirectory depth (`--max-depth`) | 32 / configurable to 64 |
| Cooperative time (`--seconds`) | 60 / configurable to 300 seconds |
| Parsed ELF files | 1,000 |
| Size of each ELF | 256 MiB |
| Total metadata read / optional hash read | 64 MiB / 512 MiB |
| Program headers / dynamic entries per ELF | 256 / 4,096 |
| Dynamic string table / each metadata string | 4 MiB / 1,024 UTF-8 bytes |
| DT_NEEDED per ELF / total references and graph edges | 256 / 10,000 |
| Displayed detailed issues | 500; additional count retained |
| Combined JSON/HTML/readme output | 16 MiB, plus a small checksum manifest |

Full-file SHA-256 is optional and applies only to supported parsed ELF inputs.
Even without hashing, metadata bytes are read. The report records read counts.
Discovery order can affect which files are reached when a budget stops the scan;
the output is explicitly partial, and limits are never converted into a pass.

Extended program-header counts, relocatable/core objects, multiple dynamic or
interpreter segments, oversized tables/strings, unsupported text and ambiguous
virtual-to-file string-table mappings are refused as coverage issues. File ranges,
load sizes, address bounds, dynamic terminators and string termination are checked.
This parser does not validate every ELF field or processor-specific convention.

Use stable files on trusted local storage. Existing symlink/junction/reparse
ancestors and encountered linked entries are refused/skipped; links are not followed
to fill a sysroot. UNC paths are refused. Mapped-network detection, blocked native
filesystem calls and concurrent adversarial path swaps are not fully controlled.
Cancellation/time checks are cooperative, not a native-operation timeout or sandbox.
Observed file identities, size and timestamps are compared around reads; this is
not an atomic snapshot or a lock against another writer restoring the same metadata.

## Privacy, provenance and contributions

Absolute user-selected root paths are not emitted: reports use `root-1/...` and
`selected-1/...` labels. Relative filenames, library names and **embedded** interpreter,
RPATH and RUNPATH strings can still identify a project. Keep actual inspection
reports private unless separately reviewed. No firmware, binary, private dataset,
phone identifier, key or original device configuration is part of this release.

Read [provenance](docs/PROVENANCE.md), [validation](docs/VALIDATION.md),
[contributing](CONTRIBUTING.md) and [security reporting](SECURITY.md).

```text
python -B source_check.py
python -B -m unittest discover -s tests -v
```

Tests generate their own bytes. A Linux-only independent check compiles two tiny
original shared libraries and compares metadata with `readelf`; those inspected
libraries are never loaded or executed. Runtime use of this tool needs neither
GCC nor binutils. Linux CI requires that oracle; Windows records its skip.

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=elf_inspector_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=elf_inspector_bug.yml).
Small invented reproductions, additional ELF cases and accessibility/report ideas
are welcome. Do not attach proprietary binaries, firmware, private reports or credentials.
