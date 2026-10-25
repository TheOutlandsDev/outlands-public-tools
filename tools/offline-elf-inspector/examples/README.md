# Generated example walkthrough

Run from this tool's directory. Pick fresh folder names in the external private
workspace each time; parents must already exist. The example writes authored ELF metadata and padding only,
not machine code, private libraries, firmware or third-party implementation.
First define `$privateWork` outside the whole checkout using the
[private workspace guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/PRIVATE-WORKSPACE.md).

## Mixed findings

```text
python -B examples/make_demo.py --destination "$privateWork/elf-demo-mixed"
python -B elf_inspector.py --file "$privateWork/elf-demo-mixed/app/demo.elf" --root "$privateWork/elf-demo-mixed/lib" --sha256 --output "$privateWork/elf-report-mixed"
```

Generator exit: 0. Inspector exit: **2**, `REVIEW_REQUIRED`.
Expected: six parsed ELF files, one ignored text file, three visited graph nodes,
six dependency edges: three unique candidates, one ambiguous, one unresolved and
one architecture mismatch. The leaf/demo cycle terminates without looping.
Open the report's `index.html` and compare `report.json`.

## No findings in this limited scope

```text
python -B examples/make_demo.py --destination "$privateWork/elf-demo-clean" --clean
python -B elf_inspector.py --file "$privateWork/elf-demo-clean/app/demo.elf" --root "$privateWork/elf-demo-clean/lib" --output "$privateWork/elf-report-clean"
```

Expected inspector exit: **0**, `NO_SCOPE_FINDINGS`, three parsed ELF files and
three unique-candidate edges, with no coverage issues. This does not make the
generated files runnable or prove any application's compatibility.

## Compare discovery and entry scope

```text
python -B elf_inspector.py --file "$privateWork/elf-demo-clean/app/demo.elf"
```

Expected exit: 2. Its dependency is unresolved because no library root was
supplied. Sibling folders are not automatically searched. Adding `--root` is
an explicit choice to inspect those files.

Reusing an existing demo/report directory is refused. Reports contain metadata,
not copies of the generated ELF files. No generated binary is included in the
GitHub source inventory. Do not execute the synthetic ELF files.
