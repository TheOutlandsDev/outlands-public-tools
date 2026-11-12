# Reviewed document dependency locks

The standalone qualification uses CPython 3.12, 3.13, 3.14 and 3.15 on Windows
x64 and Ubuntu x86-64. Each `requirements-PLATFORM-cp3XX.txt` selects exactly
three runtime distributions: `python-docx==1.2.0`, `lxml==6.1.3` and
`typing_extensions==4.16.0`. No optional extras are selected. The installer is
separate: `installer.txt` pins `pip==26.3`, which is not an application runtime
dependency. Free-threaded Python, other architectures, macOS and other Linux
distributions are outside this qualification.

The versioned official PyPI metadata links, exact wheel names, HTTPS download
URLs, byte sizes and SHA-256 values are recorded in [DEPENDENCIES.json](DEPENDENCIES.json).
Its eight `lanes` map a host/CPython ABI to one runtime lock and three wheel
records. The shared `installer` record identifies a fourth wheel and its own
lock. The two pure-Python wheels are shared; each lane has its own native lxml
wheel. There are ten unique runtime wheels and one installer wheel across the
whole matrix. Ubuntu selects the published dual-tagged
`manylinux_2_26_x86_64.manylinux_2_28_x86_64` lxml wheel; hosted Ubuntu runtime
imports and native-library versions are recorded by the actual qualification.

Only metadata and lock files are included in the source ZIP. Obtain the
selected four wheels separately from the exact recorded PyPI file URLs;
validate each filename, size and hash before use. Downloaded wheels, build
environments, generated documents and raw installation logs stay outside the
source checkout and are not release assets. No source build is permitted.

Follow the [usage guide](../USAGE.md) for the manual setup. It creates one owned
virtual environment, force-reinstalls the locked `pip==26.3` installer there,
and installs the selected three runtime wheels offline. That manual environment
contains four distributions: the three runtime dependencies plus pip. The guide
uses `$py`; it does not create separate installer/application environments.

The automated [qualification helper](../packaging/qualify.py) uses a different
environment layout: a separate owned installer environment and a fresh
application environment created with `--without-pip`. Its application environment
must contain exactly the three pinned runtime distributions, with no pip,
setuptools or unrelated distributions. The installer is checked separately.
Prepare the exact four-wheel inventory with the guide's documented
`packaging/dependencies.py --download` command, then supply that external
wheelhouse to `packaging/qualify.py`; see [qualification details](../docs/QUALIFICATION.md).

Both installation paths use `--no-index`, `--require-hashes`,
`--only-binary=:all:` and `--no-deps`. `--no-index` makes installation offline;
it does not make the initial HTTPS wheel downloads offline. `--no-deps`
prevents additional resolution because the lock already includes every mandatory
runtime dependency. Hashes bind the selected wheel bytes, and binary-only mode
refuses source builds. A hash mismatch must fail; do not remove a hash or switch
to an unlisted wheel to force an installation through.

The module-level [requirements.txt](../requirements.txt) pins the same complete
runtime closure and allows the union of the eight reviewed lxml wheel hashes.
It supports the collection's existing dependency-install entry point. The
standalone qualification deliberately uses the narrower per-lane lock instead.
There is no unbounded transitive resolver input in either form.

Official sources are [python-docx on PyPI](https://pypi.org/project/python-docx/1.2.0/),
[lxml on PyPI](https://pypi.org/project/lxml/6.1.3/),
[typing-extensions on PyPI](https://pypi.org/project/typing-extensions/4.16.0/)
and [pip on PyPI](https://pypi.org/project/pip/26.3/).
The source review checked their published release metadata and the downloaded
wheel bytes and dependency metadata. These are reproducibility controls, not a
dependency vulnerability audit, authorship verification or assurance about
arbitrary input documents. Installed lxml wheels include native libraries;
their actual linked versions belong in the runtime records. Review licenses
and applicable notices before separately redistributing any dependency wheel.
