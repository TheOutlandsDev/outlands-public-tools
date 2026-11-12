# Third-party dependency notices

This standalone ZIP contains selected OUTLANDS source under [MIT](LICENSE),
dependency selections and verification metadata. No third-party implementation,
wheel, interpreter, shared library, font or generated DOCX is included.

Document generation uses separately installed `python-docx`, `lxml` and
`typing_extensions`; the installation method also selects a separate `pip`
wheel. Their distributions retain their own licenses and notices. Review the
notices in the official distributions and retain applicable notices if you
redistribute them. The OUTLANDS MIT notice does not relicense dependencies.

The [dependency inventory](dependency-locks/DEPENDENCIES.json) records selected versions,
filenames and hashes from PyPI metadata. Artifact identity and installation
success are not a security/advisory audit or a provenance guarantee for every
upstream dependency.

Generated DOCX packages include parts from python-docx's default template,
including application metadata, styles, relationships, a thumbnail and custom
XML. They are not metadata-free outputs. No default-template implementation or
generated package is redistributed in this source ZIP.
