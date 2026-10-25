using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

namespace Outlands.ApiDiff;

public sealed record Snapshot(string Assembly, string Sha256, SortedDictionary<string, string> Declarations);
public sealed record Change(string Kind, string Id, string? Before, string? After);
public sealed record Report(int SchemaVersion, string Scope, string BeforeAssembly, string AfterAssembly, string BeforeSha256, string AfterSha256, int BeforeDeclarations, int AfterDeclarations, List<Change> Changes);

public static class Comparison
{
    public static Report Compare(Snapshot before, Snapshot after)
    {
        if (!StringComparer.Ordinal.Equals(before.Assembly, after.Assembly)) throw new AuditException("Assembly simple names differ; compare builds of the same assembly.");
        var changes = new List<Change>();
        foreach (var id in before.Declarations.Keys.Union(after.Declarations.Keys, StringComparer.Ordinal).Order(StringComparer.Ordinal))
        {
            before.Declarations.TryGetValue(id, out var oldValue); after.Declarations.TryGetValue(id, out var newValue);
            if (oldValue != newValue) changes.Add(new(oldValue is null ? "added" : newValue is null ? "removed" : "changed", id, oldValue, newValue));
        }
        return new(1, "public-declarations-only", before.Assembly, after.Assembly, before.Sha256, after.Sha256, before.Declarations.Count, after.Declarations.Count, changes);
    }
}

public sealed class Inspector
{
    public const long MaxFileBytes = 32 * 1024 * 1024;
    public const int MaxRows = 100_000, MaxDeclarations = 50_000, MaxSignatureBytes = 16_384, MaxDepth = 32, MaxElements = 1_024, MaxNameLength = 1_024;
    private readonly MetadataReader reader;
    private readonly SortedDictionary<string, string> declarations = new(StringComparer.Ordinal);
    private readonly Dictionary<TypeDefinitionHandle, bool> visibility = new();
    private int visits, totalCharacters;
    private Inspector(MetadataReader reader) { this.reader = reader; }

    public static Snapshot Inspect(string path)
    {
        LocalFiles.Validate(path, mustExist: true);
        var info = new FileInfo(path); var observedLength = info.Length; var observedWrite = info.LastWriteTimeUtc;
        byte[] bytes;
        using (var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (input.Length == 0 || input.Length > MaxFileBytes) throw new AuditException("Input exceeds the 32 MiB limit or is empty.");
            bytes = new byte[checked((int)input.Length)]; input.ReadExactly(bytes);
            if (input.ReadByte() != -1 || input.Length != bytes.Length) throw new AuditException("Input length changed during inspection.");
            info.Refresh();
            if (info.Length != observedLength || info.LastWriteTimeUtc != observedWrite) throw new AuditException("Input changed during inspection; use completed build artifacts.");
        }
        using var stream = new MemoryStream(bytes, writable: false);
        using var pe = new PEReader(stream);
        if (!pe.HasMetadata) throw new AuditException("Input has no managed metadata.");
        var metadata = pe.GetMetadataReader();
        if (!metadata.IsAssembly) throw new AuditException("Input must be an assembly, not a netmodule.");
        foreach (var table in Enum.GetValues<TableIndex>())
            if (metadata.GetTableRowCount(table) > MaxRows) throw new AuditException("Metadata table exceeds the supported row limit.");
        var instance = new Inspector(metadata);
        instance.Collect();
        return new(instance.Text(metadata.GetAssemblyDefinition().Name), Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(), instance.declarations);
    }

    private string Text(StringHandle handle)
    {
        var value = reader.GetString(handle);
        if (value.Length > MaxNameLength || value.Any(char.IsControl)) throw new AuditException("Metadata name exceeds limits or contains controls.");
        return value;
    }
    private string Id(params object[] parts) => JsonSerializer.Serialize(parts);
    private void Add(string id, params object[] details)
    {
        if (declarations.Count >= MaxDeclarations) throw new AuditException("Public declaration count exceeds the supported limit.");
        var value = JsonSerializer.Serialize(details);
        totalCharacters = checked(totalCharacters + id.Length + value.Length);
        if (id.Length > 65_536 || value.Length > 65_536 || totalCharacters > 8 * 1024 * 1024) throw new AuditException("Public declaration output exceeds supported limits.");
        if (!declarations.TryAdd(id, value)) throw new AuditException("Ambiguous duplicate API identity; comparison coverage is incomplete.");
    }
    private bool Visible(TypeDefinitionHandle handle, int depth = 0)
    {
        if (depth > MaxDepth) throw new AuditException("Type nesting exceeds the supported depth.");
        if (visibility.TryGetValue(handle, out bool value)) return value;
        var type = reader.GetTypeDefinition(handle);
        var parent = type.GetDeclaringType();
        bool result = parent.IsNil ? (type.Attributes & TypeAttributes.VisibilityMask) == TypeAttributes.Public
            : (type.Attributes & TypeAttributes.VisibilityMask) == TypeAttributes.NestedPublic && Visible(parent, depth + 1);
        visibility.Add(handle, result); return result;
    }
    private bool Public(MethodDefinitionHandle handle) => !handle.IsNil && (reader.GetMethodDefinition(handle).Attributes & MethodAttributes.MemberAccessMask) == MethodAttributes.Public;
    private string Generics(GenericParameterHandleCollection handles)
    {
        if (handles.Count > MaxElements) throw new AuditException("Generic parameter count exceeds the supported limit.");
        var result = new List<object>();
        foreach (var handle in handles)
        {
            var parameter = reader.GetGenericParameter(handle);
            var constraints = parameter.GetConstraints();
            if (constraints.Count > MaxElements) throw new AuditException("Constraint count exceeds the supported limit.");
            result.Add(new { index = parameter.Index, attributes = (int)parameter.Attributes, constraints = constraints.Select(h => TypeName(reader.GetGenericParameterConstraint(h).Type)).Order(StringComparer.Ordinal).ToArray() });
        }
        return JsonSerializer.Serialize(result.OrderBy(v => JsonSerializer.Serialize(v), StringComparer.Ordinal));
    }
    private void Collect()
    {
        foreach (var handle in reader.TypeDefinitions)
        {
            if (!Visible(handle)) continue;
            var type = reader.GetTypeDefinition(handle); var name = TypeName(handle);
            var interfaces = type.GetInterfaceImplementations();
            if (interfaces.Count > MaxElements) throw new AuditException("Interface count exceeds the supported limit.");
            Add(Id("type", name), (int)type.Attributes, TypeName(type.BaseType), interfaces.Select(h => TypeName(reader.GetInterfaceImplementation(h).Interface)).Order(StringComparer.Ordinal).ToArray(), Generics(type.GetGenericParameters()));
            foreach (var mh in type.GetMethods())
            {
                var method = reader.GetMethodDefinition(mh);
                if (!Public(mh)) continue;
                var signature = Method(method.Signature);
                Add(Id("method", name, Text(method.Name), signature.GenericCount, signature.Parameters), signature.ReturnType, signature.Header, signature.RequiredCount, (int)method.Attributes, Generics(method.GetGenericParameters()));
            }
            foreach (var fh in type.GetFields())
            {
                var field = reader.GetFieldDefinition(fh);
                if ((field.Attributes & FieldAttributes.FieldAccessMask) != FieldAttributes.Public) continue;
                var blob = Blob(field.Signature); if (blob.ReadByte() != 6) throw new AuditException("Unsupported field signature.");
                var fieldType = Decode(ref blob, 0); End(blob);
                Add(Id("field", name, Text(field.Name)), fieldType, (int)field.Attributes);
            }
            foreach (var ph in type.GetProperties())
            {
                var property = reader.GetPropertyDefinition(ph); var accessors = property.GetAccessors();
                if (!Public(accessors.Getter) && !Public(accessors.Setter)) continue;
                var signature = Method(property.Signature, property: true);
                Add(Id("property", name, Text(property.Name), signature.Parameters), signature.ReturnType, signature.Header, (int)property.Attributes, Public(accessors.Getter), Public(accessors.Setter));
            }
            foreach (var eh in type.GetEvents())
            {
                var ev = reader.GetEventDefinition(eh); var accessors = ev.GetAccessors();
                if (!Public(accessors.Adder) && !Public(accessors.Remover) && !Public(accessors.Raiser)) continue;
                Add(Id("event", name, Text(ev.Name)), TypeName(ev.Type), (int)ev.Attributes, Public(accessors.Adder), Public(accessors.Remover), Public(accessors.Raiser));
            }
        }
    }
    private static void Depth(int depth) { if (depth > MaxDepth) throw new AuditException("Signature/type nesting exceeds the supported depth."); }
    private string TypeName(EntityHandle handle, int depth = 0)
    { Visit(); return Bounded(TypeNameCore(handle, depth)); }
    private void Visit() { if (++visits > 2_000_000) throw new AuditException("Metadata decoding work exceeds supported limits."); }
    private static string Bounded(string value) { if (value.Length > 65_536) throw new AuditException("Decoded signature exceeds supported limits."); return value; }
    private string TypePart(StringHandle handle, bool ns = false)
    {
        var value = Text(handle);
        if (value.Any(c => !char.IsLetterOrDigit(c) && c != '_' && !(ns ? c == '.' : c == '`')))
            throw new AuditException("Named type contains unsupported identity delimiters or identifier characters.");
        return value;
    }
    private string ScopeName(StringHandle handle)
    {
        var value = Text(handle);
        if (value.IndexOfAny(['[', ']', ':']) >= 0) throw new AuditException("Reference scope contains unsupported identity delimiters.");
        return value;
    }
    private string TypeNameCore(EntityHandle handle, int depth)
    {
        Depth(depth); if (handle.IsNil) return "";
        switch (handle.Kind)
        {
            case HandleKind.TypeDefinition:
                var type = reader.GetTypeDefinition((TypeDefinitionHandle)handle); var parent = type.GetDeclaringType();
                if (!parent.IsNil && !type.Namespace.IsNil && Text(type.Namespace).Length != 0) throw new AuditException("Nested type namespaces outside supported scope.");
                return parent.IsNil ? Full(TypePart(type.Namespace, true), TypePart(type.Name)) : TypeName(parent, depth + 1) + "+" + TypePart(type.Name);
            case HandleKind.TypeReference:
                var reference = reader.GetTypeReference((TypeReferenceHandle)handle);
                if (reference.ResolutionScope.Kind == HandleKind.TypeReference)
                {
                    if (!reference.Namespace.IsNil && Text(reference.Namespace).Length != 0) throw new AuditException("Nested reference namespaces outside supported scope.");
                    return TypeName((TypeReferenceHandle)reference.ResolutionScope, depth + 1) + "+" + TypePart(reference.Name);
                }
                var scope = reference.ResolutionScope.Kind switch
                {
                    HandleKind.AssemblyReference => "[" + ScopeName(reader.GetAssemblyReference((AssemblyReferenceHandle)reference.ResolutionScope).Name) + "]",
                    HandleKind.ModuleReference => "[module:" + ScopeName(reader.GetModuleReference((ModuleReferenceHandle)reference.ResolutionScope).Name) + "]",
                    HandleKind.ModuleDefinition => "",
                    _ => throw new AuditException("Unsupported type reference scope.")
                };
                return scope + Full(TypePart(reference.Namespace, true), TypePart(reference.Name));
            case HandleKind.TypeSpecification:
                var blob = Blob(reader.GetTypeSpecification((TypeSpecificationHandle)handle).Signature);
                var result = Decode(ref blob, depth + 1); End(blob); return result;
            default: throw new AuditException("Unsupported metadata type handle.");
        }
    }
    private static string Full(string ns, string name) => ns.Length == 0 ? name : ns + "." + name;
    private BlobReader Blob(BlobHandle handle)
    {
        var blob = reader.GetBlobReader(handle);
        if (blob.Length == 0 || blob.Length > MaxSignatureBytes) throw new AuditException("Signature exceeds supported byte limits.");
        return blob;
    }
    private static void End(BlobReader blob) { if (blob.RemainingBytes != 0) throw new AuditException("Signature has unsupported trailing data."); }
    private static int Count(ref BlobReader blob)
    {
        int count = blob.ReadCompressedInteger();
        if (count < 0 || count > MaxElements) throw new AuditException("Signature element count exceeds the supported limit.");
        return count;
    }
    private sealed record Signature(byte Header, int GenericCount, int RequiredCount, string ReturnType, string[] Parameters);
    private Signature Method(BlobHandle handle, bool property = false)
    { var blob = Blob(handle); var result = DecodeMethod(ref blob, 0, property); End(blob); return result; }
    private Signature DecodeMethod(ref BlobReader blob, int depth, bool property = false)
    {
        Depth(depth); byte header = blob.ReadByte(); int convention = header & 15;
        if ((header & 0x80) != 0 || (property ? convention != 8 : convention is not (0 or 1 or 2 or 3 or 4 or 5 or 9 or 11)))
            throw new AuditException("Unsupported method/property calling convention.");
        int generic = (header & 16) != 0 ? Count(ref blob) : 0;
        int count = Count(ref blob); var returnType = Decode(ref blob, depth + 1); var parameters = new string[count]; int required = count;
        for (int i = 0; i < count; i++)
        {
            var peek = blob;
            if (peek.ReadByte() == 0x41)
            {
                if (convention != 5 || required != count) throw new AuditException("Invalid vararg sentinel.");
                blob.ReadByte(); required = i;
            }
            parameters[i] = Decode(ref blob, depth + 1);
        }
        return new(header, generic, required, returnType, parameters);
    }
    private string Decode(ref BlobReader blob, int depth)
    { Visit(); return Bounded(DecodeCore(ref blob, depth)); }
    private string DecodeCore(ref BlobReader blob, int depth)
    {
        Depth(depth); byte code = blob.ReadByte();
        switch (code)
        {
            case 0x01: return "System.Void"; case 0x02: return "System.Boolean"; case 0x03: return "System.Char";
            case 0x04: return "System.SByte"; case 0x05: return "System.Byte"; case 0x06: return "System.Int16"; case 0x07: return "System.UInt16";
            case 0x08: return "System.Int32"; case 0x09: return "System.UInt32"; case 0x0a: return "System.Int64"; case 0x0b: return "System.UInt64";
            case 0x0c: return "System.Single"; case 0x0d: return "System.Double"; case 0x0e: return "System.String";
            case 0x0f: return Decode(ref blob, depth + 1) + "*"; case 0x10: return Decode(ref blob, depth + 1) + "&";
            case 0x11: return "valuetype(" + TypeName(blob.ReadTypeHandle(), depth + 1) + ")";
            case 0x12: return "class(" + TypeName(blob.ReadTypeHandle(), depth + 1) + ")";
            case 0x13: return "!" + Count(ref blob);
            case 0x14:
                var element = Decode(ref blob, depth + 1); int rank = Count(ref blob); int sizeCount = Count(ref blob);
                if (rank < 1 || sizeCount > rank) throw new AuditException("Invalid array shape.");
                var sizes = new int[sizeCount]; for (int i = 0; i < sizes.Length; i++) sizes[i] = blob.ReadCompressedInteger();
                int boundCount = Count(ref blob); if (boundCount > rank) throw new AuditException("Invalid array bounds.");
                var bounds = new int[boundCount]; for (int i = 0; i < bounds.Length; i++) bounds[i] = blob.ReadCompressedSignedInteger();
                return "array(" + element + ";rank=" + rank + ";sizes=" + string.Join(",", sizes) + ";lower=" + string.Join(",", bounds) + ")";
            case 0x15:
                byte kind = blob.ReadByte(); if (kind is not (0x11 or 0x12)) throw new AuditException("Invalid generic type signature.");
                var name = TypeName(blob.ReadTypeHandle(), depth + 1); int count = Count(ref blob); var arguments = new string[count];
                for (int i = 0; i < count; i++) arguments[i] = Decode(ref blob, depth + 1);
                return (kind == 0x11 ? "valuetype(" : "class(") + name + "<" + string.Join(",", arguments) + ">)";
            case 0x16: return "System.TypedReference"; case 0x18: return "System.IntPtr"; case 0x19: return "System.UIntPtr";
            case 0x1b:
                var method = DecodeMethod(ref blob, depth + 1); return "fnptr(" + JsonSerializer.Serialize(method) + ")";
            case 0x1c: return "System.Object"; case 0x1d: return Decode(ref blob, depth + 1) + "[]"; case 0x1e: return "!!" + Count(ref blob);
            case 0x1f: case 0x20:
                var modifier = TypeName(blob.ReadTypeHandle(), depth + 1); return (code == 0x1f ? "modreq(" : "modopt(") + modifier + ")" + Decode(ref blob, depth + 1);
            case 0x45: return "pinned(" + Decode(ref blob, depth + 1) + ")";
            default: throw new AuditException("Unsupported or malformed signature element.");
        }
    }
}
