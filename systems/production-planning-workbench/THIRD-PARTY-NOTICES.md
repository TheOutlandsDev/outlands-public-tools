# Separately installed dependencies

The authored application is MIT, copyright TheOutlandsDev. Dependency code,
runtimes, installed environments and wheels are not bundled in its source ZIP.
Installing dependencies retains their own notices and terms; this application's
MIT license does not relicense them.

| Dependency | Pin | Upstream terms |
| --- | --- | --- |
| Pydantic | 2.12.5 | [MIT](https://github.com/pydantic/pydantic/blob/v2.12.5/LICENSE) |
| pydantic-core | 2.41.5 | [MIT](https://github.com/pydantic/pydantic-core/blob/v2.41.5/LICENSE) |
| annotated-types | 0.7.0 | [MIT](https://github.com/annotated-types/annotated-types/blob/v0.7.0/LICENSE) |
| typing-extensions | 4.15.0 | [Python Software Foundation terms](https://github.com/python/typing_extensions/blob/4.15.0/LICENSE) |
| typing-inspection | 0.4.2 | [MIT](https://github.com/pydantic/typing-inspection/blob/v0.4.2/LICENSE) |

The [requirements](requirements.txt) bind the selected PyPI wheel SHA-256 values
for CPython 3.12/3.13 Windows x64 and glibc Linux x86_64. These pins establish
download identity, not a claim of universal security or platform compatibility.
See the [Pydantic release metadata](https://pypi.org/pypi/pydantic/2.12.5/json).
Python, pip, SQLite and OS APIs are separately supplied under their own terms.
No third-party implementation is imported from the original operating project.
