using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.CompilerServices;
namespace Example;
internal static class ExecutionTrap
{
    [ModuleInitializer] internal static void Init() { var p = Environment.GetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP"); if (p != null) File.WriteAllText(p, "executed"); }
}
internal class Hidden { public class Nested { public void SecretChanged() { } } }
public interface IPlugin { void Run(); }
public class Plugin : IPlugin
{
    public long Level;
    public const int Constant = 2;
    public string Name { get; private set; } = "sample";
    public event Action? Completed { add { } remove { } }
    public void Run() => throw new Exception("Do not execute fixture methods");
    public long Convert(int value) => value;
    public string Convert(string value) => value;
    public void Added() { }
    protected void ProtectedChanged() { }
    private void PrivateChanged() { }
    public class Nested { public int Read() => 0; }
    private class PrivateNested { public void InvisibleChanged() { } }
}
public unsafe class Shapes<T> where T : class, new()
{
    public T Identity(T input) => input;
    public U Generic<U>(U input) where U : struct => input;
    public ref int Ref(ref int value) => ref value;
    public int* Pointer(int* value) => value;
    public int[,] Matrix(int[,] value) => value;
    public List<T[]> List(List<T[]> value) => value;
    public delegate* unmanaged[Cdecl]<int, int> Callback(delegate* unmanaged[Cdecl]<int, int> value) => value;
    public volatile int Flag;
    public int this[int index] => index;
}
