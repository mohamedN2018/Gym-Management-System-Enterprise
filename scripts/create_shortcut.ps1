# Create a "Gym ERP" shortcut on the Desktop pointing at the built executable.
# Run after building:  powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1
$root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $root "build\nuitka\launcher.dist\GymERP.exe"
$icon = Join-Path $root "assets\icon.ico"

if (-not (Test-Path $exe)) {
    Write-Error "Executable not found. Build it first: python scripts/build.py"
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$linkPath = Join-Path $desktop "Gym ERP.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path $exe -Parent
if (Test-Path $icon) { $shortcut.IconLocation = $icon }
$shortcut.Description = "Gym ERP - Gym Management System"
$shortcut.Save()
Write-Output "Desktop shortcut created: $linkPath"
