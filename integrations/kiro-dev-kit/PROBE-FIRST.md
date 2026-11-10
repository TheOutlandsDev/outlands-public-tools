# Read-only probe before installation

The package starts with `START-HERE.ps1`. Run it in ordinary Windows
PowerShell 5.1 or PowerShell 7 from the extracted source package:

```powershell
./START-HERE.ps1
```

It needs neither Python nor administrator elevation. It verifies listed
source files against `PACKAGE-MANIFEST.json` before invoking the two bundled
read-only metadata inspectors. It never runs the installer, a discovered
runtime, a project command, sign-in, or an endpoint request. The console
report is not written to a file by the package. Normal OS auditing and shell
history are outside this script's control. If policy blocks execution, keep
that result and use the company's deployment process; do not change policy.

The manifest establishes listed-file consistency, not a digital publisher
signature or authority to install. Obtain the package through the reviewed
GitHub source or another approved distribution route. A modified entry point
cannot authenticate itself. Extra files are not certified by this manifest.

## Inspect a selected repository

The project path is optional and must be supplied explicitly:

```powershell
$project = Read-Host 'Existing repository folder to inspect'
./START-HERE.ps1 -Repository $project
```

The scanner defaults to depth 2 and 500 filesystem entries. Maximum supported
settings are depth 4 and 2,000 entries. It reads only recognized manifest
files up to 256 KiB, skips inspected links/reparse points, and excludes common
credential, VCS, virtual-environment, dependency, and build-output directories.
It does not import a Python project, evaluate Gradle, resolve a Maven parent,
read lockfile contents, execute package scripts, install dependencies, or
probe a network. Source parsing is deliberately bounded and incomplete.

Reports omit the absolute repository path, project/package names, and raw
script contents. Evidence includes a record ID, manifest basename, and field
or section. `-IncludeRelativePaths` explicitly adds private relative evidence
paths; keep that report in the approved project environment. No report should
be uploaded publicly without review.

| Manifest | Static observations | Important boundary |
| --- | --- | --- |
| `pyproject.toml`, `setup.cfg` | Simple literal Python requirement; pytest/ruff/mypy section hints | Not a full TOML/INI parser or dependency resolver |
| `.python-version` | Numeric interpreter declaration | Does not install or launch that interpreter |
| `package.json` | Node engine text, package manager, standard script names | Script bodies are withheld and never executed |
| Node lock filenames | Manager presence and conflicting managers | Lockfile content and dependency health are not read |
| `pom.xml` | Numeric Java properties/compiler configuration, wrapper filenames | XML DTDs prohibited; parents, profiles and properties unresolved |
| Gradle build files | Literal `JavaLanguageVersion.of`/`jvmToolchain` hints and wrapper filenames | Build code and dynamic values are never evaluated |

Python 3.15.2 range checks support simple numeric `>=`, `>`, `<=`, `<`, `==`,
and `!=` clauses, including comma conjunctions and equality/inequality prefix
wildcards. Other expressions stay UNKNOWN. A permitted declaration is not a
passing install, test, dependency, or runtime result. Poetry requirements,
multi-line or complex syntax, dynamic build logic, and all Node engine-range
semantics require further review. Native races and hardlink provenance are
not qualified; inspect an ordinary stable project directory.

## Review the output before deciding on installation

1. Package hash failure: stop and compare with the reviewed source.
2. Missing metadata/runtime: arrange the prerequisite through the approved
   process. PATH absence or missing file-version metadata is not proof that
   software is uninstalled; a WindowsApps alias is not a working interpreter.
3. Project conflicts: keep its declared toolchains and investigate compatibility
   before proposing a Python 3.15 migration.
4. Candidate commands: every command is PROPOSED_NOT_EXECUTED. Inspect the
   source scripts and project instructions before any later authorized run.
5. Device policy, organization sign-in, model access, and Bedrock permissions:
   these remain unknown or unverified. A read-only probe cannot approve them.

There is no automatic transition from probe to installation. After reviewing
the report and obtaining any required organization approval, the separate
Python 3.15 installer can preview project-file changes. `-Apply` is the
explicit write step described in [README.md](README.md). This package contains
source and methods, not Python, Java, Node, Kiro installers or credentials.

The repository inspector is also available after installation as
`.kiro/devkit/Inspect-Repository.ps1` for the developer agent's read-only
onboarding tasks. It provides candidate context for Kiro steering, not
automatically generated or overwritten project instructions.

Sources: [Python project metadata](https://packaging.python.org/en/latest/specifications/pyproject-toml/),
[npm package metadata](https://docs.npmjs.com/cli/configuring-npm/package-json/),
[Maven Java targeting](https://maven.apache.org/guides/mini/guide-java-target.html),
and [Gradle toolchains](https://docs.gradle.org/current/userguide/toolchains.html).
