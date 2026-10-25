# Provenance and MIT scope

A local inspect_gpt.py helper provided an offline binary layout-inspection use case. Its original whole-file read and signature scan were replaced with bounded explicit metadata reads and new validation.

The owner identified the local helpers as personal work. The public parser,
reports, generated fixtures and tests are fresh original code, with reusable
first-party MIT file/report helpers from the existing collection. Original local
helpers remain intact and are fingerprinted in the private review record. No
firmware, actual image/config, vendor binary/source, device-specific recipe or
real diagnostic report is included. This is a selected-source review, not
independent proof of exclusive authorship of every historical local project.

MIT covers the new original source, authored docs/tests and fictional generators.
No upstream parser/runtime implementation is vendored or relicensed. Python and
its bundled libraries retain their applicable terms. Inspected inputs retain
their own ownership/licenses, irrespective of the report status.

Design background was checked against [primary format documentation](https://uefi.org/specs/UEFI/2.11/05_GUID_Partition_Table_Format.html)
on 2026-10-25. A separate [primary format reference](https://github.com/tianocore/edk2/blob/master/MdePkg/Include/Uefi/UefiGpt.h) was also consulted. The published implementation is its own documented subset;
it does not port upstream implementation code or copy real format examples.

Validation uses generated data only. No actual disk/device, firmware image,
module binary, kernel, HAL service, boot, mount or deployment was tested.
