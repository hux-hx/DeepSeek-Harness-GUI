# DeepSeek Harness Desktop (Windows) Installer
# Creates Start Menu and Desktop shortcuts for the Electron app.
# Run:  powershell -ExecutionPolicy Bypass -File install-windows.ps1

$ErrorActionPreference = 'Stop'

$AppDir = Split-Path -Parent $PSScriptRoot   # the repo/app root (windows/..)
$Exe    = Join-Path $AppDir 'DeepSeek-Harness-Desktop.exe'
$Ico    = Join-Path $AppDir 'share\icons\windows\deepseek-harness-desktop.ico'

Write-Host "== DeepSeek Harness Desktop (Windows) install =="

# Prerequisite: dsh must be installed globally
if (Get-Command dsh -ErrorAction SilentlyContinue) {
    Write-Host "  dsh: OK"
} else {
    Write-Warning "dsh not found. Install the harness first:"
    Write-Host "  npm i -g @deepseek-ai/dsh"
}

if (-not (Test-Path $Ico)) { $Ico = '' }

$shell = New-Object -ComObject WScript.Shell

# Create Start Menu shortcut
$startMenuDir = Join-Path $shell.SpecialFolders('StartMenu') 'Programs\DeepSeek Harness'
if (-not (Test-Path $startMenuDir)) { New-Item -ItemType Directory -Path $startMenuDir | Out-Null }
$shortcuts = @(
    (Join-Path $startMenuDir 'DeepSeek Harness.lnk'),
    (Join-Path $shell.SpecialFolders('Desktop') 'DeepSeek Harness.lnk')
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

# If .exe exists, link to it; otherwise fall back to launcher.js
if (Test-Path $Exe) {
    New-Shortcut $shortcuts[0] $Exe $Ico 'DeepSeek Harness desktop GUI'
    New-Shortcut $shortcuts[1] $Exe $Ico 'DeepSeek Harness desktop GUI'
} else {
    # Fallback: use PowerShell to run launcher.js
    $psTarget = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $AppDir 'launcher.js')`""
    New-Shortcut $shortcuts[0] $psTarget $Ico 'DeepSeek Harness desktop GUI (Node.js launcher)'
    New-Shortcut $shortcuts[1] $psTarget $Ico 'DeepSeek Harness desktop GUI (Node.js launcher)'
}

Write-Host "installed shortcuts:"
$shortcuts | ForEach-Object { Write-Host "  $_" }
Write-Host ""
Write-Host "Configuration is imported automatically from %USERPROFILE%\.dsh on first launch."
Write-Host "App data is stored in: %APPDATA%\DeepSeekHarnessDesktop"
Write-Host ""
Write-Host "To build the .exe installer, run:"
Write-Host "  cd windows"
Write-Host "  npm install"
Write-Host "  npx electron-builder --win --x64"
