# Private inspection workspace

Keep image files and generated reports outside the source checkout, in a local
private directory you control. Select an existing absolute parent and a new
report directory for each run. Use only stable regular raw-image files you are
allowed to inspect. Examples use invented images rather than actual disks.

The default report omits disk/partition GUIDs and partition names. Metadata
hashes, numeric layouts and optional details can still identify an input; this
is not anonymization. Review reports before sharing them. The source release
contains authored code and fictional generators, not images or actual reports.

The inspector reads bounded metadata and writes new reports. It does not mount
or repair an image, access physical drives, or establish filesystem contents,
bootability, authenticity, device compatibility or suitability for flashing.
Path/handle checks and cooperative budgets are best effort, not an OS sandbox,
an atomic snapshot or a hard deadline against a hostile filesystem. An I/O
failure may leave a new partial report directory; resolve the cause and select
a different fresh output. The unsigned manifest checks report consistency.
