# Private inspection workspace

Keep sparse image files and generated reports outside the source checkout in a
private local directory you control. Select a stable ordinary file and a new
report directory whose absolute parent already exists. Examples use fictional
image structures generated in that private workspace.

Only bounded sparse headers are inspected. RAW, FILL and CRC bodies and header
extensions remain unread; declared output blocks are counted without generating
an expanded image. CRC declarations remain explicitly unverified. Metadata
hashes and numeric layouts can identify an input; reports are not anonymized.
Keep actual images and reports private and review any report before sharing it.

The inspector does not reconstruct, mount, repair or flash an image, open a
physical device or execute payloads. A metadata result does not establish
payload integrity, authenticity, filesystem contents, bootability or device
compatibility. Path/handle checks and cooperative bounds are best effort, not
an OS sandbox, atomic snapshot or hard native I/O deadline. A write failure may
leave a new partial report folder; resolve the cause and choose another fresh
output. The unsigned manifest verifies report consistency only.
