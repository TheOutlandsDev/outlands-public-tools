# OUTLANDS | App Affinity Launcher

Launch a chosen Windows application with an explicit CPU affinity and working
directory. This tool generalizes the owner's small game-launch wrapper into a
reusable command-line program. It provides a non-launching plan, literal child
arguments, a best-effort duplicate check, and a JSON launch receipt.

The original source, tests, documentation and fictional examples are
[MIT licensed](LICENSE), as part of
[OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools).
Python and Windows are supplied separately under their own terms. No game,
application executable, operating-system DLL or dependency implementation is
bundled. See [provenance](docs/PROVENANCE.md) and
[dependency records](docs/DEPENDENCIES.json).

**A successful receipt proves the recorded launch setup, not application
readiness, game stability, improved performance or compatibility.** Native tests
use disposable Python children. No game is launched to qualify this release.
Read the [validation record](docs/VALIDATION.md) for actual test scope and skips.

## Start without launching anything

Install Python **3.12 or 3.13** and open a terminal in
`tools/app-affinity-launcher`. The application uses the standard library; no
`pip install` is required. Native launch support targets 64-bit Windows 10/11.

```text
python -m app_affinity --help
python -m app_affinity demo
python -B source_check.py
```

No arguments displays help. Help and the fictional demo make no Windows API
calls, start no application and write no receipt file. `launcher.py` is a
compatibility entry point for the same program.

Portable policy/demo tests can run on Ubuntu. Real application planning and
launching require Windows; native tests are explicitly skipped elsewhere.

## Plan a launch

Use an existing absolute local path to a `.exe` file you intend to run. The
following paths are fictional and must be replaced with your own. Choose logical
processor IDs that are available to the launcher process.

```text
python -m app_affinity plan --exe "D:\Apps\Example App\Example.exe" --cores 0
python -m app_affinity plan --exe "D:\Apps\Example App\Example.exe" --cores 0,2 --cwd "D:\Apps\Example App"
python -m app_affinity plan --exe "D:\Apps\Example App\Example.exe" --mask 0x5 -- --example "two words"
```

`plan` validates the selected files and Windows capabilities and queries visible
process paths for a duplicate. It does **not** create a process, change affinity,
edit an application, change the registry or write configuration. An invalid or
unavailable selection is refused. In particular, processor 0 may be unavailable
when the launcher itself has a restricted affinity; the examples do not bypass
that restriction.

The JSON includes the available mask and selected settings. Review it privately
before using `launch`. It contains executable paths, working directories and
arguments and is not automatically suitable for a public issue report.

## Launch explicitly

Change the verb to `launch` only when you want to start the selected application:

```text
python -m app_affinity launch --exe "D:\Apps\Example App\Example.exe" --cores 0
python -m app_affinity launch --exe "D:\Apps\Example App\Example.exe" --mask 0x5 --cwd "D:\Apps\Example App" -- --example "two words"
```

The launcher revalidates the plan, supplies the executable as an explicit
`CreateProcessW` application name, and creates its primary thread suspended at
normal priority. It sets the new child's affinity, reads back the mask and
priority, and then resumes that thread. A setup failure attempts to terminate
only that newly created child through its owned process handle; cleanup status
is surfaced. Existing applications are not terminated or assigned a new mask.

The launcher does not invoke a command shell, request administrator rights,
search `PATH` for the executable, install anything or persist affinity settings.
Child arguments after `--` are passed as arguments using Windows command-line
quoting. Characters such as `&` and `|` are not executed by a shell in the
launcher. Each target application still defines its own argument interpretation.

The default working directory is the executable's parent. Use `--cwd` for an
explicit existing absolute local directory. Arguments are not expanded as shell
variables or wildcards by the launcher.
There may be at most 256 child arguments. The complete quoted Windows command
line must fit 32,767 UTF-16 code units including its terminating NUL.

## Affinity and duplicate rules

| Option or rule | Meaning |
| --- | --- |
| `--cores 0,2` | Zero-based **logical processor** IDs; not physical-core or performance-core labels. Repeated or invalid IDs are refused. |
| `--mask 0x5` | Nonzero hexadecimal bit mask: bits 0 and 2 select logical processors 0 and 2. Use either cores or mask. |
| Available processors | The requested mask must fit the pointer width and be a subset of the launcher's current allowed mask. |
| Processor groups | This initial release refuses machines with more than one active processor group; it does not silently choose a group. |
| Executable | Existing regular absolute local `.exe`; no batch files, shortcuts, UNC/device paths, mapped network drives or linked/reparse input paths and parents. |
| Duplicates | A visible matching full executable path is refused by default. This is not a cross-user or atomic single-instance guarantee. |
| `--allow-existing` | Explicitly permit another instance of the selected executable. Useful when testing with the same Python executable as the launcher. |
| `--no-window` | Requests `CREATE_NO_WINDOW` for a console child. It does not hide a GUI application's window. |

Duplicate detection is best effort. Access restrictions can prevent querying a
process's full path; bounded enumeration can also be incomplete. Receipts report
visibility limits. Another process can start after the check, and the selected
application may enforce its own single-instance behavior.
Windows dot segments and path components ending in a dot or space are refused.
Other file aliases can still differ from the visible process-path string; this
check does not establish unique file identity across every alias or hard link.

Only the selected newly created process is configured. An application can later
change its own affinity, delegate work to another process or use a separate
launcher. These mechanisms are outside this receipt. A one-processor selection
is not a universal fix and may reduce performance. Test the intended application
separately before adopting a setting.

## Waiting, receipts and exit codes

Without `--wait`, the launcher returns after the recorded setup/resume. The
application can continue running. To observe it for a bounded time:

```text
python -m app_affinity launch --exe "D:\Apps\Example App\Example.exe" --cores 0 --wait 10
```

`--wait` accepts a finite number of seconds greater than zero and at most 300.
The receipt reports the child's exit code if observed, or a wait timeout. A wait
timeout leaves a resumed application running. Ctrl+C during the wait also leaves
it running and exits the launcher with code 130; it is not an application-stop
command. Close that application through its normal controls.

Receipts include the action, whether launch was requested, selected paths and
arguments, and, after launch, the PID, verified pre-resume mask/priority and
resume state. Wait fields report observations of that specific child. No receipt
is automatically saved. Terminal output and any shell redirection can retain
private paths/arguments; keep real receipts private.

| Launcher exit code | Meaning |
| --- | --- |
| `0` | Help/demo or validated plan/launch completed. A waited child's nonzero exit is reported in the receipt, not copied into the launcher exit code. |
| `2` | Validation, refusal or native setup error. Inspect the structured error and any cleanup result. |
| `130` | Interrupted wait; an already resumed child is left running. |

## Try disposable examples and tests

The [example guide](examples/README.md) includes an original child fixture that
records its own starting affinity, priority, arguments and working directory to
an explicitly supplied **new** JSON file. Use a disposable private folder and
read the commands before running them. It contains no game or third-party app.

```text
python -B -m unittest discover -s tests -v
```

The test suite includes portable policy/lifecycle cases with fake backends and
native Windows cases that start generated disposable Python children. It never
launches your game to count a test as passed. Off-Windows skips are not native
passes. See [validation](docs/VALIDATION.md).

## Troubleshooting and suggestions

If a path is refused, use a supported regular local file/directory and inspect
the selected path instead of disabling checks. If a mask is refused, select
logical processors present in the reported available mask. Multi-group support
requires additional implementation and validation. No elevated retry is made.

A launch receipt can succeed even if the application subsequently fails to
initialize. Check the target application's normal diagnostics separately. This
tool does not repair game profiles, libraries, display settings or save files.

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=app_affinity_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=app_affinity_bug.yml).
Include the source commit, Windows/Python versions and a small fictional
reproduction. Share only redacted receipts and examples you have rights to
publish. See [contributing](CONTRIBUTING.md), [security/privacy](SECURITY.md) and
the [Windows API references](docs/DEPENDENCIES.json).
