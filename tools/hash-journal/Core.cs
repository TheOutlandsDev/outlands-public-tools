// Original MIT implementation. No historical wallet, network or vendor code copied.
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Outlands.HashJournal;

public sealed class JournalException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

public sealed record JournalRecord(int Sequence, string Previous, string Text, string Hash);
public sealed record Verification(int Count, string Head, string Anchor, bool? ExpectedCountMatched);

public static class Journal
{
    public const int MaxBytes = 1_048_576;
    public const int MaxLineBytes = 65_536;
    public const int MaxRecords = 10_000;
    public const int MaxTextBytes = 8_192;
    public const string Zero = "0000000000000000000000000000000000000000000000000000000000000000";
    public const string Domain = "outlands-hash-journal-v1\n";
    private static readonly UTF8Encoding Utf8 = new(false, true);

    public static bool IsHash(string? value) => value is { Length: 64 }
        && value.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f');

    public static void ValidateText(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) throw new JournalException("EMPTY_TEXT");
        try
        {
            if (Utf8.GetByteCount(text) > MaxTextBytes) throw new JournalException("TEXT_BYTE_LIMIT");
        }
        catch (EncoderFallbackException) { throw new JournalException("INVALID_UNICODE"); }
    }

    public static string ComputeHash(int sequence, string previous, string text)
    {
        if (sequence < 1 || sequence > MaxRecords) throw new JournalException("SEQUENCE_LIMIT");
        if (!IsHash(previous)) throw new JournalException("INVALID_PREVIOUS_HASH");
        ValidateText(text);
        string material = Domain + sequence.ToString(CultureInfo.InvariantCulture) + "\n" + previous + "\n" + text;
        return Convert.ToHexString(SHA256.HashData(Utf8.GetBytes(material))).ToLowerInvariant();
    }

    public static JournalRecord NewRecord(int sequence, string previous, string text)
        => new(sequence, previous, text, ComputeHash(sequence, previous, text));

    public static Verification Verify(IReadOnlyList<JournalRecord> records, string? expectedHead = null, int? expectedCount = null)
    {
        if (expectedHead is not null && !IsHash(expectedHead)) throw new JournalException("INVALID_EXPECTED_HEAD");
        if (expectedCount is < 1 or > MaxRecords) throw new JournalException("INVALID_EXPECTED_COUNT");
        if (records.Count is < 1 or > MaxRecords) throw new JournalException("RECORD_LIMIT");
        string previous = Zero;
        for (int index = 0; index < records.Count; index++)
        {
            JournalRecord record = records[index];
            if (record.Sequence != index + 1) throw new JournalException("SEQUENCE_MISMATCH");
            if (record.Previous != previous) throw new JournalException("PREVIOUS_MISMATCH");
            if (!IsHash(record.Hash)) throw new JournalException("INVALID_HASH");
            string computed = ComputeHash(record.Sequence, record.Previous, record.Text);
            if (!CryptographicOperations.FixedTimeEquals(Convert.FromHexString(record.Hash), Convert.FromHexString(computed)))
                throw new JournalException("HASH_MISMATCH");
            previous = record.Hash;
        }
        if (expectedHead is not null && previous != expectedHead) throw new JournalException("EXPECTED_HEAD_MISMATCH");
        if (expectedCount is not null && records.Count != expectedCount) throw new JournalException("EXPECTED_COUNT_MISMATCH");
        return new(records.Count, previous, expectedHead is null ? "UNANCHORED" : "HEAD_MATCHED", expectedCount is null ? null : true);
    }

    public static IReadOnlyList<JournalRecord> Parse(byte[] bytes)
    {
        if (bytes.Length is < 1 or > MaxBytes) throw new JournalException("INPUT_BYTE_LIMIT");
        if (bytes.Length >= 3 && bytes[0] == 0xef && bytes[1] == 0xbb && bytes[2] == 0xbf) throw new JournalException("BOM_UNSUPPORTED");
        if (bytes[^1] != (byte)'\n') throw new JournalException("FINAL_LF_REQUIRED");
        if (bytes.Contains((byte)'\r')) throw new JournalException("CRLF_UNSUPPORTED");
        try { _ = Utf8.GetString(bytes); }
        catch (DecoderFallbackException) { throw new JournalException("INVALID_UTF8"); }
        var records = new List<JournalRecord>();
        int start = 0;
        for (int index = 0; index < bytes.Length; index++)
        {
            if (bytes[index] != (byte)'\n') continue;
            int length = index - start;
            if (length is < 1 or > MaxLineBytes) throw new JournalException("LINE_BYTE_LIMIT");
            if (records.Count == MaxRecords) throw new JournalException("RECORD_LIMIT");
            records.Add(ParseLine(bytes.AsMemory(start, length)));
            start = index + 1;
        }
        Verify(records);
        return records.AsReadOnly();
    }

    private static JournalRecord ParseLine(ReadOnlyMemory<byte> line)
    {
        try
        {
            using JsonDocument document = JsonDocument.Parse(line, new JsonDocumentOptions { MaxDepth = 8 });
            JsonElement root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object) throw new JournalException("RECORD_OBJECT_REQUIRED");
            var members = new HashSet<string>(StringComparer.Ordinal);
            foreach (JsonProperty member in root.EnumerateObject())
            {
                if (!members.Add(member.Name)) throw new JournalException("DUPLICATE_PROPERTY");
                if (member.Name is not ("schema" or "sequence" or "previous" or "text" or "hash")) throw new JournalException("UNKNOWN_PROPERTY");
            }
            if (members.Count != 5) throw new JournalException("MISSING_PROPERTY");
            JsonElement schema = root.GetProperty("schema"), sequence = root.GetProperty("sequence");
            if (schema.ValueKind != JsonValueKind.Number || !schema.TryGetInt32(out int version) || version != 1)
                throw new JournalException("UNSUPPORTED_SCHEMA");
            if (sequence.ValueKind != JsonValueKind.Number || !sequence.TryGetInt32(out int number)) throw new JournalException("INVALID_SEQUENCE");
            string ReadString(string name)
            {
                JsonElement value = root.GetProperty(name);
                if (value.ValueKind != JsonValueKind.String) throw new JournalException("STRING_PROPERTY_REQUIRED");
                return value.GetString() ?? throw new JournalException("STRING_PROPERTY_REQUIRED");
            }
            return new(number, ReadString("previous"), ReadString("text"), ReadString("hash"));
        }
        catch (JsonException) { throw new JournalException("INVALID_JSON"); }
        catch (InvalidOperationException) { throw new JournalException("INVALID_JSON_TEXT"); }
    }

    public static byte[] Encode(IReadOnlyList<JournalRecord> records)
    {
        // Freeze the caller's selected immutable records before validating/encoding.
        if (records.Count is < 1 or > MaxRecords) throw new JournalException("RECORD_LIMIT");
        JournalRecord[] copy = records.ToArray();
        Verify(copy);
        using var output = new MemoryStream();
        foreach (JournalRecord record in copy)
        {
            byte[] line = JsonSerializer.SerializeToUtf8Bytes(new
            {
                schema = 1, sequence = record.Sequence, previous = record.Previous, text = record.Text, hash = record.Hash
            });
            if (line.Length > MaxLineBytes) throw new JournalException("LINE_BYTE_LIMIT");
            if (output.Length + line.Length + 1 > MaxBytes) throw new JournalException("OUTPUT_BYTE_LIMIT");
            output.Write(line); output.WriteByte((byte)'\n');
        }
        return output.ToArray();
    }

    private static string CheckedPath(string path, bool input)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(path) || path.IndexOf('\0') >= 0 || !Path.IsPathFullyQualified(path)) throw new JournalException("ABSOLUTE_PATH_REQUIRED");
            if (path.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar).Any(part => part is "." or "..")) throw new JournalException("AMBIGUOUS_PATH");
            _ = Utf8.GetByteCount(path);
            string full = Path.GetFullPath(path);
            if (OperatingSystem.IsWindows())
            {
                if (path.StartsWith("\\\\", StringComparison.Ordinal) || path.StartsWith("//", StringComparison.Ordinal)) throw new JournalException("NETWORK_OR_DEVICE_PATH");
                string? root = Path.GetPathRoot(full);
                if (root is null || new DriveInfo(root).DriveType is DriveType.Network or DriveType.Unknown or DriveType.NoRootDirectory)
                    throw new JournalException("LOCAL_DRIVE_REQUIRED");
                if (path.Length > 2 && path[2..].IndexOf(':') >= 0) throw new JournalException("ALTERNATE_STREAM_UNSUPPORTED");
                if (path[3..].Split('\\', '/').Any(part => part.EndsWith(' ') || part.EndsWith('.'))) throw new JournalException("AMBIGUOUS_PATH");
            }
            string? parent = Path.GetDirectoryName(full);
            if (parent is null) throw new JournalException("PARENT_DIRECTORY_REQUIRED");
            var parents = new List<string>();
            for (string? current = parent; current is not null; current = Path.GetDirectoryName(current))
            {
                parents.Add(current);
            }
            // Check from root toward leaf, so an observed linked ancestor is
            // refused before inspecting a descendant through that link.
            parents.Reverse();
            foreach (string current in parents)
            {
                FileAttributes attributes;
                try { attributes = File.GetAttributes(current); }
                catch (Exception error) when (error is FileNotFoundException or DirectoryNotFoundException)
                { throw new JournalException("PARENT_DIRECTORY_REQUIRED"); }
                if ((attributes & FileAttributes.ReparsePoint) != 0) throw new JournalException("LINKED_PATH");
                if ((attributes & FileAttributes.Directory) == 0) throw new JournalException("PARENT_DIRECTORY_REQUIRED");
            }
            try
            {
                FileAttributes leaf = File.GetAttributes(full);
                if ((leaf & FileAttributes.ReparsePoint) != 0) throw new JournalException("LINKED_PATH");
                if ((leaf & FileAttributes.Directory) != 0) throw new JournalException("REGULAR_FILE_REQUIRED");
                if (!input) throw new JournalException("OUTPUT_EXISTS");
            }
            catch (FileNotFoundException) { if (input) throw new JournalException("INPUT_UNAVAILABLE"); }
            catch (DirectoryNotFoundException) { throw new JournalException("PARENT_DIRECTORY_REQUIRED"); }
            return full;
        }
        catch (EncoderFallbackException) { throw new JournalException("INVALID_UNICODE"); }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or ArgumentException or NotSupportedException)
        { throw new JournalException("PATH_UNAVAILABLE"); }
    }

    public static IReadOnlyList<JournalRecord> ReadFile(string path)
    {
        string full = CheckedPath(path, true);
        try
        {
            var before = new FileInfo(full);
            long length = before.Length;
            DateTime modified = before.LastWriteTimeUtc;
            // Empty files and zero-length special files (including FIFOs) are rejected before opening.
            if (length is < 1 or > MaxBytes) throw new JournalException("INPUT_BYTE_LIMIT");
            using var stream = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (!stream.CanSeek || stream.Length != length) throw new JournalException("REGULAR_FILE_REQUIRED");
            using var buffer = new MemoryStream();
            byte[] block = new byte[4096];
            while (true)
            {
                int read = stream.Read(block, 0, (int)Math.Min(block.Length, MaxBytes + 1L - buffer.Length));
                if (read == 0) break;
                buffer.Write(block, 0, read);
                if (buffer.Length > MaxBytes) throw new JournalException("INPUT_BYTE_LIMIT");
            }
            before.Refresh();
            if (buffer.Length != length || before.Length != length || before.LastWriteTimeUtc != modified) throw new JournalException("INPUT_CHANGED");
            return Parse(buffer.ToArray());
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or NotSupportedException)
        { throw new JournalException("INPUT_READ_FAILED"); }
    }

    public static void WriteFresh(string path, IReadOnlyList<JournalRecord> records)
    {
        byte[] data = Encode(records); // Validate the complete selection before creating any output.
        string full = CheckedPath(path, false);
        try
        {
            var options = new FileStreamOptions { Mode = FileMode.CreateNew, Access = FileAccess.Write, Share = FileShare.None, Options = FileOptions.WriteThrough };
            if (!OperatingSystem.IsWindows()) options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
            using var stream = new FileStream(full, options);
            stream.Write(data); stream.Flush(true);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or NotSupportedException)
        { throw new JournalException("OUTPUT_WRITE_FAILED_PARTIAL_POSSIBLE"); }
    }

    public static Verification Create(string output, string text)
    {
        JournalRecord[] records = [NewRecord(1, Zero, text)];
        WriteFresh(output, records); return Verify(records);
    }

    public static Verification Append(string input, string output, string text)
    {
        JournalRecord[] old = ReadFile(input).ToArray();
        if (old.Length == MaxRecords) throw new JournalException("RECORD_LIMIT");
        JournalRecord[] updated = [.. old, NewRecord(old.Length + 1, old[^1].Hash, text)];
        WriteFresh(output, updated); return Verify(updated);
    }
}
