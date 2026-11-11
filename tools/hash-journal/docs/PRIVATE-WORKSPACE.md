# Private workspace

Extract each release source ZIP into a fresh source directory. Choose a
separate user-owned private directory for SDKs, build artifacts, journals,
anchors, test files and qualification reports. Keep private inputs, generated
builds and downloaded prerequisites outside the source folder and public
repositories.

A fictional arrangement is:

```text
source/hash-journal-0.2.0/       extracted public source only
private/hash-journal/
  sdk10/                       separately downloaded SDK 10.0.404
  sdk11/                       separately downloaded SDK 11.0.100
  build10/                     generated net10.0 application files
  build11/                     generated net11.0 application files
  journals/                    selected private journal versions
  anchors/                     independently retained expected heads/counts
  qualification/               disposable extraction/build/test work and reports
```

Choose the real locations yourself. Journal commands require absolute paths
and existing parent directories. They do not create a workspace, search for
journals or choose a default destination. Portable prerequisites can normally
be extracted into user-owned folders without administrator access. Follow
your device's software policy and do not bypass restrictions. Required system
libraries or organization-controlled installations may need separate handling.

Use trusted local storage and quiescent paths. Observed symlinks/reparse
components are refused. Windows UNC/device/alternate-stream paths and mapped
network drives are unsupported. Unix mount topology is not an isolation
boundary. Link and input size/time checks have race windows; they cannot
contain hostile concurrent filesystem replacement.

`append` preserves its selected input and creates a new file. Keep old versions
when comparing or recovering your work. Existing outputs are refused. A failed
fresh write can leave a partial output; inspect that selected file privately
and choose another new filename. The tool does not delete files as recovery.

Journals contain complete event text in clear text. Use suitable directory
permissions and your normal backups. Unix output requests owner-only mode;
Windows inherits the parent ACL. Neither gives encryption, immutability or
automatic retention. Shell history, CLI arguments, OS records and redirection
can retain text, filenames and metadata too.

Keep expected head and count in a separately trusted place for later
replacement/truncation checks. Reading the expected head from the journal
being checked provides no independent anchor. A matching head does not
establish authorship, truth, time or continuous retention.

SDK archives, runtime files, generated binaries and raw diagnostics stay
outside the source release. Publish the reviewed source ZIP, sanitized
qualification summary and designated release metadata. Public bug reports
should use fresh fictional events and omit private paths, accounts, machine
names, real journals, credentials and proprietary material. See
[USAGE.md](../USAGE.md) and [SECURITY.md](../SECURITY.md).
