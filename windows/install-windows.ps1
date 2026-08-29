# DeepSeek Harness Desktop (Windows) per-user installer.
# Creates Start Menu and Desktop shortcuts and checks prerequisites.
# Run from a normal PowerShell:  powershell -ExecutionPolicy Bypass -File install-windows.ps1
$ErrorActionPreference = 'Stop'

$AppDir = Split-Path -Parent $PSScriptRoot   # the repo/app root (windows/..)
$AppCmd = Join-Path $PSScriptRoot 'DeepSeek-Harness-Desktop.cmd'
$HubCmd = Join-Path $PSScriptRoot 'DeepSeek-Harness-Plugin-Hub.cmd'
$Ico    = Join-Path $AppDir 'share\icons\windows\deepseek-harness-desktop.ico'

Write-Host "== DeepSeek Harness Desktop (Windows) install =="

# Prerequisite checks (advisory, non-fatal where the app degrades gracefully).
$pythonOk = $false
foreach ($exe in 'pythonw.exe', 'py.exe') {
  if (Get-Command $exe -ErrorAction SilentlyContinue) { $pythonOk = $true }
}
if (-not $pythonOk) {
  Write-Warning "Python 3 not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH' and tcl/tk)."
} else {
  Write-Host "  python: OK"
}
if (Get-Command dsh -ErrorAction SilentlyContinue) {
  Write-Host "  dsh: OK"
} else {
  Write-Warning "dsh not found. Install the harness first:  npm i -g @deepseek-ai/dsh"
}
try {
  python -c "import webview" 2>$null
  if ($LASTEXITCODE -eq 0) { Write-Host "  pywebview: OK" }
  else { throw 'missing' }
} catch {
  Write-Warning "pywebview missing. Install it:  py -3 -m pip install pywebview"
}

if (-not (Test-Path $Ico)) { $Ico = '' }

$shell = New-Object -ComObject WScript.Shell
$targets = @(
  (Join-Path $shell.SpecialFolders('StartMenu') 'Programs\DeepSeek Harness Desktop.lnk'),
  (Join-Path $shell.SpecialFolders('Desktop') 'DeepSeek Harness Desktop.lnk'),
  (Join-Path $shell.SpecialFolders('Desktop') 'DeepSeek Harness Plugin Hub.lnk')
)

function New-Shortcut($Path, $Target, $Icon, $Desc) {
  $dir = Split-Path -Parent $Path
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  $lnk = $shell.CreateShortcut($Path)
  $lnk.TargetPath = $Target
  $lnk.WorkingDirectory = Split-Path -Parent $Target
  if ($Icon) { $lnk.IconLocation = "$Icon,0" }
  $lnk.Description = $Desc
  $lnk.Save()
}

New-Shortcut $targets[0] $AppCmd $Ico 'DeepSeek Harness desktop GUI (dsh web in a native window)'
New-Shortcut $targets[1] $AppCmd $Ico 'DeepSeek Harness desktop GUI (dsh web in a native window)'
New-Shortcut $targets[2] $HubCmd  $Ico 'Built-in dsh plugin hub'

Write-Host "installed shortcuts:"
$targets | ForEach-Object { Write-Host "  $_" }
Write-Host ""
Write-Host "Configuration is imported automatically from %USERPROFILE%\.dsh on first launch."
Write-Host "Uninstall: delete the shortcuts above and the %APPDATA%\DeepSeekHarnessDesktop data folder."
