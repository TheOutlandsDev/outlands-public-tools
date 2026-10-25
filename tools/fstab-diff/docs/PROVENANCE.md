# Provenance and license scope

A local shell helper hashed and text-diffed selected fstab variants during a private phone investigation.

This publication is a fresh original bounded parser, CLI, reports, tests and
authored fictional fixtures. The original local helper remains unchanged and
is retained separately. Only its generic inspection use case informed this
tool; extraction, device paths, hardware recipes, vendor content and stock
implementations are not included or copied into the public source.

MIT covers the new original source and documentation, including first-party
`text_support.py` duplicated across the three standalone module folders. The
Python runtime remains separately licensed and is not bundled. No external
parser library or firmware implementation is vendored. Inputs and inspected
payloads retain their existing rights; inspection never grants MIT to them.

Format background was checked against [primary format source](https://man7.org/linux/man-pages/man5/fstab.5.html) on
2026-10-25. The implementation uses its own narrower documented grammar and
does not port upstream source. Upstream license notices apply to upstream
material, not to a new blanket relicensing of device/build configurations.

Android field interpretation was also checked against the [AOSP fstab reader](https://android.googlesource.com/platform/system/core/+/refs/heads/main/fs_mgr/libfstab/fstab.cpp).

Local validation uses only generated files. No phone, real firmware, build,
boot, mount or successful device recovery was tested or is implied.
