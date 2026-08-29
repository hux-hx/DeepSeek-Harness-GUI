param(
    [string]$TargetPath = "$PSScriptRoot\launcher.js",
    [string]$IconPath = "$PSScriptRoot\share\icons\windows\deepseek-harness-desktop.ico"
)

$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$Desktop\DeepSeek Harness.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c `"$TargetPath`""
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = $IconPath
$Shortcut.Description = "DeepSeek Harness Desktop"
$Shortcut.Save()
Write-Host "Created desktop shortcut: $Desktop\DeepSeek Harness.lnk"
