# XML Recipe Inspector 0.1.0

Inspect a supplied unnamespaced recipe XML and export structural JSON/CSV
summaries. Windows/Ubuntu, regular CPython 3.12–3.15; standard library only.
Supply Python separately. No administrator session, activation script, package
installation or cloud account is needed. Managed execution controls still apply.

## Download and verify

Download `xml-recipe-inspector-0.1.0.zip`, `USAGE.md`, `VALIDATION.json`,
`build-manifest.json` and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/xml-recipe-inspector-v0.1.0).
The checksums cover every other attached asset. Check the exact ZIP name/digest
before extracting into a fresh local directory.

PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\xml-recipe-inspector-0.1.0.zip
Get-Content .\SHA256SUMS.txt
```

Ubuntu, with all downloaded assets in the current directory:

```sh
sha256sum --check SHA256SUMS.txt
```

Checksums establish matching bytes, not independent publisher identity. Keep
`xml_recipe_inspector.py` and `xml_windows.py` together. The ZIP includes source,
notices, tests and build/qualification methods, with no runtime, dependency
implementation, actual recipe, image, report or credential.

## First use: fictional XML

From the extracted tool directory, check `python --version` and
`python -B xml_recipe_inspector.py --help`. Use `python3` on Ubuntu if that
selects the intended interpreter. In an existing trusted private scratch
directory outside the extracted app, create a fictional `example.xml`:

```xml
<Recipe>
  <PixelSize><X>0.25</X></PixelSize>
  <Modules><Module><ID>fictional-module</ID></Module></Modules>
  <Measurements/>
</Recipe>
```

Substitute absolute private paths in this command. The output directory must
be new and its parent must already exist:

```text
python -B xml_recipe_inspector.py ABSOLUTE_PRIVATE_EXAMPLE_XML --out-dir ABSOLUTE_NEW_PRIVATE_OUTPUT_DIRECTORY
```

This minimal example returns counts-only stdout JSON: status `ok`, one module,
zero measurements, zero overlay rows and three files written. Reopen
`modules_summary.json`, `measurements_summary.json` and
`overlay_line_line_summary.json` in the new directory. Optional missing geometry
is JSON `null`; no image file is needed or opened. Recipes with accepted overlay
rows also produce `overlay_line_line_summary.csv`.

Repeat with the same destination: it must return status 2 and fixed stderr JSON
with `OUTPUT_EXISTS`, preserving the existing directory and input. Use another
new destination for another export. Help needs no input/output. Malformed
arguments return `ARGUMENTS_INVALID` without echoing supplied values.

## Parser and output safeguards

Only regular bounded inputs are accepted. DTDs, entity declarations, external
entities and processing instructions are refused, including UTF-16 declarations.
Ordinary character references are allowed; XML namespaces are unsupported.
Input is limited to 1 MiB, depth 64, 20,000 elements, 1,048,576 text characters
and 2,048 characters per selected field. Combined rendered output is bounded
at 4 MiB before directory creation. Nonfinite calibration/geometry and derived
numeric overflow are refused. CSV text that could start a spreadsheet formula
gets a leading apostrophe; JSON intentionally retains its original text.

Existing output files/directories/links are not replaced and missing parents
are not created. POSIX requests directory mode 0700 and report mode 0600.
Windows uses retained native handles, rejects unsafe links/paths and inherits
the selected parent's ACL; no equivalent mode or ACL privacy audit is supplied.
Use stable trusted local parents and quiescent files.

An error after output creation can leave an empty, partial or unconfirmed new
directory. Inspect it privately and choose a fresh destination; do not regard
it as a successful export. Windows performs no pathname-deletion rollback.
Neither backend establishes an immutable/atomic report set, hostile-race
containment, filesystem snapshot or hardware/power-loss durability.

## Interpretation and privacy

This is a structural inspector. It does not run vendor software, detect image
edges, fit measurement lines, validate a vendor algorithm or establish physical
measurement accuracy. It retains the original first-descendant `PixelSize/X`
calibration for both midpoint axes. The first two PointProperty blocks supply
midpoint differences only when each has exactly two user points. Review whether
those conventions fit your recipe before interpreting outputs.

Real recipes and reports may contain identifiers, locations, geometry and
calibration-derived values. They are not anonymized. Inspect only material you
are authorized to use, keep outputs/tracebacks private, and review sharing rights.
No URL fetching, XInclude expansion, image loading, command execution or package
installation is performed from XML.

## Qualification

The attached VALIDATION.json records eight actual Windows/Ubuntu × Python
3.12, 3.13, 3.14 and 3.15.2 lanes, exact patches/Expat versions, ZIP hash and
execution counts. Each imports from a fresh extraction in a new dependency-free
venv and reproduces exact archive bytes. All 89 methods run, including five
copied-runtime CLI tests with socket/process actions denied and self-checked.
CI requires Windows native hardlinks, symlinks and junctions. Opposite-platform
cases and unavailable alternate short-name spellings are explicit skips.

The two runtime modules remain unchanged; shared tests now apply each platform's
documented permission/error contract. No real recipe, image or original program
was executed. Network/virtual filesystems, hostile concurrent mutation, Windows
ACL confidentiality, free-threaded Python, other architectures, vendor accuracy
and hardware durability remain unqualified. See [the full contract](README.md),
[Windows details](docs/WINDOWS.md) and [qualification method](docs/PYTHON315.md).
