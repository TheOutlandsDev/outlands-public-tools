using System.Text;
using System.Text.Json;

namespace Outlands.ApiDiff;

public static class Program
{
    public static readonly JsonSerializerOptions Json = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    public static int Main(string[] args)
    {
        if (args.Length == 0 || args is ["--help"])
        {
            Console.WriteLine(".NET Public API Diff (trusted build artifacts only)\nUsage: ApiDiff compare --before OLD.dll --after NEW.dll [--output NEW.json]\nRead-only metadata comparison. Exit 0 equal; 1 declarations differ; 2 invalid input/coverage error.\nReports contain API names and hashes. Review before sharing. Output files must not exist.");
            return 0;
        }
        try
        {
            if (args[0] != "compare") throw new AuditException("Expected compare command.");
            var values = new Dictionary<string, string>(StringComparer.Ordinal);
            for (int i = 1; i < args.Length; i += 2)
            {
                if (i + 1 >= args.Length || args[i] is not ("--before" or "--after" or "--output") || !values.TryAdd(args[i], args[i + 1]))
                    throw new AuditException("Invalid, duplicate, or incomplete option.");
            }
            if (!values.TryGetValue("--before", out var before) || !values.TryGetValue("--after", out var after))
                throw new AuditException("Both --before and --after are required.");
            var result = Comparison.Compare(Inspector.Inspect(before), Inspector.Inspect(after));
            var text = JsonSerializer.Serialize(result, Json) + "\n";
            if (values.TryGetValue("--output", out var output))
            {
                LocalFiles.Validate(output, mustExist: false);
                using var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None);
                var bytes = new UTF8Encoding(false, true).GetBytes(text);
                stream.Write(bytes);
            }
            else Console.Write(text);
            return result.Changes.Count == 0 ? 0 : 1;
        }
        catch (AuditException ex) { Console.Error.WriteLine("Error: " + ex.Message); return 2; }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or BadImageFormatException or ArgumentException or InvalidOperationException or OverflowException or IndexOutOfRangeException)
        { Console.Error.WriteLine("Error: input/output could not be processed; no comparison is complete."); return 2; }
    }
}

public sealed class AuditException(string message) : Exception(message);

public static class LocalFiles
{
    public static void Validate(string path, bool mustExist)
    {
        if (string.IsNullOrWhiteSpace(path) || path.Any(char.IsControl) || path.StartsWith("\\\\", StringComparison.Ordinal) || path.StartsWith("//", StringComparison.Ordinal))
            throw new AuditException("A regular local path is required.");
        var full = Path.GetFullPath(path);
        if (OperatingSystem.IsWindows() && full[2..].Contains(':')) throw new AuditException("Alternate data streams are not supported.");
        var current = mustExist ? full : Path.GetDirectoryName(full)!;
        if (mustExist && (!File.Exists(full) || Directory.Exists(full))) throw new AuditException("Input must be a regular existing file.");
        if (!mustExist && !Directory.Exists(current)) throw new AuditException("Output parent must already exist.");
        while (!string.IsNullOrEmpty(current))
        {
            if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new AuditException("Symbolic links and reparse points are not supported.");
            current = Path.GetDirectoryName(current);
        }
    }
}
