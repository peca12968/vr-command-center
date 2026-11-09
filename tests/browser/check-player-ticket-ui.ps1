param(
    [Parameter(Mandatory)][int]$LauncherPid,
    [Parameter(Mandatory)][string]$ExpiredConfig,
    [Parameter(Mandatory)][string]$CurrentConfig,
    [Parameter(Mandatory)][string]$LoadLabel,
    [Parameter(Mandatory)][string]$PlayLabel,
    [Parameter(Mandatory)][string]$SeatText,
    [Parameter(Mandatory)][string]$ExpiredText,
    [Parameter(Mandatory)][string]$RemainingText
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TicketUiWindow
{
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll")]
    public static extern bool IsWindowEnabled(IntPtr window);
    [DllImport("user32.dll", EntryPoint = "SendMessageTimeoutW", CharSet = CharSet.Unicode)]
    private static extern IntPtr SetTextMessage(IntPtr window, uint message, IntPtr w, string value, uint flags, uint timeout, out IntPtr result);
    [DllImport("user32.dll", EntryPoint = "SendMessageTimeoutW")]
    private static extern IntPtr ButtonMessage(IntPtr window, uint message, IntPtr w, IntPtr l, uint flags, uint timeout, out IntPtr result);

    public static bool SetText(IntPtr window, string text)
    {
        IntPtr result;
        return SetTextMessage(window, 0x000C, IntPtr.Zero, text, 2, 2000, out result) != IntPtr.Zero && result != IntPtr.Zero;
    }
    public static bool Click(IntPtr window)
    {
        IntPtr result;
        return ButtonMessage(window, 0x00F5, IntPtr.Zero, IntPtr.Zero, 2, 3000, out result) != IntPtr.Zero;
    }
}
'@
$automation = [System.Windows.Automation.AutomationElement]
$descendants = [System.Windows.Automation.TreeScope]::Descendants

function Wait-For($Condition, [string]$Label) {
    $deadline = [Diagnostics.Stopwatch]::StartNew()
    do {
        $value = & $Condition
        if ($value) { return $value }
        Start-Sleep -Milliseconds 100
    } while ($deadline.Elapsed.TotalSeconds -lt 8)
    throw "Launcher UI did not show $Label."
}

$window = Wait-For {
    $child = Get-Process -Id $LauncherPid
    if ($child.MainWindowHandle -ne [IntPtr]::Zero) {
        $element = $automation::FromHandle($child.MainWindowHandle)
        if ($element.Current.ProcessId -eq $LauncherPid) { $element }
    }
} 'its owned window'

function Find-Control([string]$ClassPrefix, [string]$Label = '') {
    $elements = @($window.FindAll($descendants, [System.Windows.Automation.Condition]::TrueCondition) |
        Where-Object { $_.Current.ClassName.StartsWith($ClassPrefix) -and (!$Label -or $_.Current.Name -ceq $Label) })
    if ($elements.Count -eq 1) { return $elements[0] }
}

function Owned-Handle($Element) {
    $handle = [IntPtr]$Element.Current.NativeWindowHandle
    $owner = [uint32]0
    if ([TicketUiWindow]::GetWindowThreadProcessId($handle, [ref]$owner) -eq 0 -or $owner -ne $LauncherPid) {
        throw 'Launcher control no longer belongs to the owned process.'
    }
    return $handle
}

$pathBox = Wait-For { Find-Control 'WindowsForms10.EDIT.' } 'the path box'
$load = Find-Control 'WindowsForms10.BUTTON.' $LoadLabel
$play = Find-Control 'WindowsForms10.BUTTON.' $PlayLabel

function Has-Text([string]$Text) {
    foreach ($element in $window.FindAll($descendants, [System.Windows.Automation.Condition]::TrueCondition)) {
        if ($element.Current.ClassName.StartsWith('WindowsForms10.STATIC.') -and $element.Current.Name.Contains($Text)) { return $true }
    }
    return $false
}

function Play-Enabled { return [TicketUiWindow]::IsWindowEnabled((Owned-Handle $play)) }
if (![TicketUiWindow]::SetText((Owned-Handle $pathBox), $ExpiredConfig) -or
    ![TicketUiWindow]::Click((Owned-Handle $load))) { throw 'Could not load the expired fixture.' }
[void](Wait-For { (Has-Text $SeatText) -and (Has-Text $ExpiredText) -and (Play-Enabled) } 'expired estimate with launch available')
if (![TicketUiWindow]::SetText((Owned-Handle $pathBox), $CurrentConfig)) { throw 'Could not enter the signed file path.' }
[void](Wait-For { !(Has-Text $ExpiredText) -and !(Play-Enabled) } 'cleared preview before reload')
if (![TicketUiWindow]::Click((Owned-Handle $load))) { throw 'Could not load the signed file.' }
[void](Wait-For { (Has-Text $SeatText) -and (Has-Text $RemainingText) -and (Play-Enabled) } 'the signed file seat and remaining time')
if (![TicketUiWindow]::Click((Owned-Handle $play))) { throw 'Could not start the owned player.' }
[void](Wait-For { (Has-Text $SeatText) -and !(Has-Text $RemainingText) -and !(Play-Enabled) } 'the active game seat without a countdown')
[Console]::WriteLine('{"expiredWarning":true,"changedFileCleared":true,"currentSeatAndTime":true,"launchKeepsSeat":true}')
