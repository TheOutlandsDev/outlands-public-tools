const LOCAL_HEADER_SIZE = 30;
const CENTRAL_HEADER_SIZE = 46;
const END_HEADER_SIZE = 22;
const UINT16_MAX = 0xffff;
const UINT32_MAX = 0xffffffff;
const UTF8_FLAG = 1 << 11;
const DOS_DATE = 0x21; // 1980-01-01, the earliest standard ZIP date.

const crcTable = Uint32Array.from({ length: 256 }, (_, value) => {
  for (let bit = 0; bit < 8; bit += 1) {
    value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
  }
  return value;
});

function crc32(bytes) {
  let crc = UINT32_MAX;
  for (const byte of bytes) {
    crc = (crc >>> 8) ^ crcTable[(crc ^ byte) & 0xff];
  }
  return (crc ^ UINT32_MAX) >>> 0;
}

function writeFileMetadata(view, offset, { filename, bytes, checksum }) {
  // These fields occur in the same order in the local and central records.
  view.setUint16(offset, 20, true); // ZIP version 2.0.
  view.setUint16(offset + 2, UTF8_FLAG, true);
  // Method 0 (stored) and midnight are already zero.
  view.setUint16(offset + 8, DOS_DATE, true);
  view.setUint32(offset + 10, checksum, true);
  view.setUint32(offset + 14, bytes.length, true); // Stored size.
  view.setUint32(offset + 18, bytes.length, true); // Uncompressed size.
  view.setUint16(offset + 22, filename.length, true);
}

// Wheels are already compressed; method 0 packages them without recompressing.
export function createZip(entries) {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder("utf-8", { ignoreBOM: true });
  const names = new Set();
  const files = [];
  let localSize = 0;
  let centralSize = 0;

  for (const [name, bytes] of entries) {
    if (typeof name !== "string" || /[\\:*?"<>|\x00-\x1f\x7f]/u.test(name)
        || name.split("/").some(part => !part || /[ .]$/u.test(part))) {
      throw new Error("ZIP entry names must be safe relative paths.");
    }
    if (!(bytes instanceof Uint8Array)) {
      throw new TypeError("ZIP entry contents must be a Uint8Array.");
    }
    // Compare the encoded name so malformed Unicode cannot create duplicates.
    const filename = encoder.encode(name);
    const key = decoder.decode(filename).toLowerCase();
    if (names.has(key)) {
      throw new Error("ZIP entry names must be unique.");
    }
    names.add(key);

    const offset = localSize;
    localSize += LOCAL_HEADER_SIZE + filename.length + bytes.length;
    centralSize += CENTRAL_HEADER_SIZE + filename.length;
    if (filename.length > UINT16_MAX || files.length + 1 >= UINT16_MAX
        || localSize + centralSize + END_HEADER_SIZE >= UINT32_MAX) {
      throw new RangeError("Selection is too large for a standard ZIP.");
    }
    files.push({ filename, bytes, checksum: crc32(bytes), offset });
  }

  const archive = new Uint8Array(localSize + centralSize + END_HEADER_SIZE);
  const view = new DataView(archive.buffer);
  let centralOffset = localSize;

  for (const file of files) {
    const { offset, filename, bytes } = file;
    view.setUint32(offset, 0x04034b50, true);
    writeFileMetadata(view, offset + 4, file);
    archive.set(filename, offset + LOCAL_HEADER_SIZE);
    archive.set(bytes, offset + LOCAL_HEADER_SIZE + filename.length);

    view.setUint32(centralOffset, 0x02014b50, true);
    view.setUint16(centralOffset + 4, 20, true); // ZIP version made by.
    writeFileMetadata(view, centralOffset + 6, file);
    view.setUint32(centralOffset + 42, offset, true);
    archive.set(filename, centralOffset + CENTRAL_HEADER_SIZE);
    centralOffset += CENTRAL_HEADER_SIZE + filename.length;
  }

  view.setUint32(centralOffset, 0x06054b50, true);
  view.setUint16(centralOffset + 8, files.length, true);
  view.setUint16(centralOffset + 10, files.length, true);
  view.setUint32(centralOffset + 12, centralSize, true);
  view.setUint32(centralOffset + 16, localSize, true);
  return archive;
}
