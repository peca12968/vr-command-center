const { execFileSync, spawnSync } = require('node:child_process');
const { realpathSync } = require('node:fs');
const path = require('node:path');

function locate(executable, cwd) {
  const where = path.join(process.env.SystemRoot, 'System32', 'where.exe');
  return execFileSync(where, [executable], { cwd, windowsHide: true, encoding: 'utf8', timeout: 5000 })
    .split(/\r?\n/)[0].trim();
}

function requireSilentWindowsLaunch(root, executable) {
  if (process.platform !== 'win32') return;
  const program = realpathSync.native(executable);
  let powershell;
  try {
    powershell = locate('pwsh.exe', root);
  } catch {
    powershell = path.join(process.env.SystemRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
  }
  const checker = path.join(root, 'scripts', 'check-windows-firewall-notifications.ps1');
  const result = spawnSync(powershell,
    ['-NoLogo', '-NoProfile', '-NonInteractive', '-File', checker, '-Executable', program],
    { env: { ...process.env, VR_COMMAND_UNATTENDED: '1' }, windowsHide: true, encoding: 'utf8', timeout: 15000 });
  if (result.status !== 0) {
    const reason = result.stderr?.trim() || result.error?.message || `check exited with code ${result.status}`;
    throw new Error(`Startup skipped for ${path.basename(program)}. ${reason}`);
  }
}

function checkedLoopbackHost(root) {
  if (process.platform !== 'win32') return 'dotnet';
  const dotnet = locate('dotnet.exe', root);
  requireSilentWindowsLaunch(root, dotnet);
  requireSilentWindowsLaunch(root, process.execPath);
  return dotnet;
}

module.exports = checkedLoopbackHost;
module.exports.requireSilentWindowsLaunch = requireSilentWindowsLaunch;
