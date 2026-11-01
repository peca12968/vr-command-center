using System;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Web.Script.Serialization;

internal static class ReportPublicationProof
{
    public sealed class Value
    {
        public static readonly ManualResetEvent Entered = new ManualResetEvent(false), Release = new ManualResetEvent(false);
        public string status { get { Entered.Set(); if (!Release.WaitOne(5000)) throw new InvalidOperationException("Serializer gate expired"); return "ready"; } }
    }
    private static int Main(string[] args)
    {
        var method = Assembly.LoadFrom(args[0]).GetType("ControlLauncher").GetMethod("SaveNew", BindingFlags.NonPublic | BindingFlags.Static);
        Exception error = null;
        var worker = new Thread(() => { try { method.Invoke(null, new object[] { args[1], new Value() }); } catch (Exception value) { error = value; } }); worker.Start();
        if (!Value.Entered.WaitOne(3000)) { Value.Release.Set(); return 2; }
        var visible = File.Exists(args[1]); long? bytes = visible ? new FileInfo(args[1]).Length : (long?)null;
        Value.Release.Set(); if (!worker.Join(5000) || error != null) return 3;
        var contents = File.ReadAllText(args[1]); var valueResult = new { passed = !visible, serializerBlockedFinalVisible = visible, finalBytesWhileBlocked = bytes, finalContent = contents,
            scope = "Actual compiled SaveNew via reflection / controlled serializer getter. Method-level evidence, not original OS scheduling or whole application-domain proof." };
        using (var report = new FileStream(args[2], FileMode.CreateNew, FileAccess.Write)) using (var text = new StreamWriter(report)) text.Write(new JavaScriptSerializer().Serialize(valueResult));
        return visible ? 1 : 0;
    }
}
