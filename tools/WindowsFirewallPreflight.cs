using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Text;

internal sealed class WindowsFirewallPreflight : IOException
{
    private WindowsFirewallPreflight(string executable, bool mayPrompt)
        : base(Path.GetFileName(executable) + (mayPrompt
            ? " 的 Windows 防火牆可能顯示允許視窗，已略過啟動。"
            : " 的 Windows 防火牆查核未完成，已略過啟動。")) { }

    internal static void Require(string executable)
    {
        int result;
        try { result = Check(Path.GetFullPath(executable)); }
        catch (Win32Exception) { result = -1; }
        catch (InvalidOperationException) { result = -1; }
        catch (IOException) { result = -1; }
        if (result != 0) throw new WindowsFirewallPreflight(executable, result == 2);
    }

    private static int Check(string executable)
    {
        using (var resource = typeof(WindowsFirewallPreflight).Assembly.GetManifestResourceStream("FirewallPreflight.ps1"))
        {
            if (resource == null) return -1;
            using (var reader = new StreamReader(resource, Encoding.UTF8))
            {
                // Pass the path as data, including quotes and non-ASCII characters in package paths.
                var command = "try { & {\n" + reader.ReadToEnd() + "\n} -Executable $env:VRCOMMAND_FIREWALL_IMAGE\nexit $LASTEXITCODE } catch { exit 1 }";
                var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(command));
                var powershell = Path.Combine(Environment.SystemDirectory, @"WindowsPowerShell\v1.0\powershell.exe");
                var info = new ProcessStartInfo(powershell, "-NoLogo -NoProfile -NonInteractive -EncodedCommand " + encoded)
                { UseShellExecute = false, CreateNoWindow = true };
                info.EnvironmentVariables["VRCOMMAND_FIREWALL_IMAGE"] = executable;
                using (var process = Process.Start(info))
                {
                    if (process == null) return -1;
                    if (process.WaitForExit(15000)) return process.ExitCode;
                    process.Kill();
                    return -1;
                }
            }
        }
    }
}
