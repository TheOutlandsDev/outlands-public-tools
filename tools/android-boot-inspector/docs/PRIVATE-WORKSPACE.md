# Private inspection workspace

Keep images and generated reports outside the source checkout in a private
local directory you control. Select a stable regular local file and an existing
absolute parent for a new report directory. Examples use fictional non-bootable
images. Keep real firmware and reports private.

The inspector reads bounded headers and supported vendor table metadata. Kernel,
ramdisk, DTB, signature, bootconfig and padding payloads remain unread. Names,
board IDs, physical addresses and command lines are omitted from reports, but
metadata hashes and numeric layouts can identify a build; this is not anonymization.
Review reports before sharing them.

Declared offsets and signature placement do not establish signature/AVB validity,
bootability, authenticity, reconstruction or device compatibility. The source ZIP
contains generators rather than binary images or interpreters. Path/handle checks
and cooperative limits are best effort, not an OS sandbox, atomic snapshot or
hard I/O deadline. A failed write may leave a new partial report directory;
resolve the cause and choose a fresh output. The unsigned manifest checks report
consistency, not authenticity.
