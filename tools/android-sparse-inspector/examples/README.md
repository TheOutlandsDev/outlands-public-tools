# Fictional sparse examples

`generate.py --output NEW_ABSOLUTE_DIRECTORY` writes three tiny invented files:
`valid.sparse`, `crc-unverified.sparse` and `truncated.sparse`. The parent must
already exist. The destination must be new. Run the inspector commands in the
[main guide](../README.md) using separate fresh report directories.

The valid image declares four 4-byte output blocks: one RAW block with `DEMO`,
one FILL block with an arbitrary four-byte pattern, and two DONT_CARE blocks.
No expanded image is written. The CRC example adds an unverified checksum chunk;
the truncated example removes a byte from the final chunk header.

Expected exits are 0, 1 and 1 respectively. These are synthetic format fixtures,
not firmware, application packages or device-compatibility evidence. Generated
files and reports belong in private work directories outside the source tree.
