# NexusTrader — Create Desktop Shortcut
# Run this ONCE to place a shortcut on your Desktop.
# After that, just double-click the shortcut to launch the app.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath     = Join-Path $projectRoot "NexusTrader.vbs"
$iconPath    = "C:\Windows\System32\shell32.dll"   # built-in Windows icon
$iconIndex   = 40   # green arrow icon in shell32

$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "NexusTrader.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = "wscript.exe"
$shortcut.Arguments        = "`"$vbsPath`""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description      = "Start NexusTrader (Backend + Frontend)"
$shortcut.IconLocation     = "$iconPath,$iconIndex"
$shortcut.WindowStyle      = 1
$shortcut.Save()

Write-Host ""
Write-Host "  Shortcut created on Desktop: NexusTrader.lnk" -ForegroundColor Green
Write-Host "  Double-click it any time to start the app."    -ForegroundColor Cyan
Write-Host ""
