param(
    [string]$Executable = "",
    [string]$Profile = "",
    [switch]$StartWithWindows
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Executable) {
    $Executable = Join-Path $ProjectRoot "dist\WaterBuddyPet.exe"
}
$Executable = [System.IO.Path]::GetFullPath($Executable)
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "WaterBuddyPet.exe was not found. Run windows_companion\build.ps1 first."
}
if (-not $Profile) {
    $Profile = Join-Path $ProjectRoot "data\water_buddy.json"
}
$Profile = [System.IO.Path]::GetFullPath($Profile)

$Shell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
foreach ($Folder in @($Desktop)) {
    $ShortcutPath = Join-Path $Folder "WaterBuddy Pet.lnk"
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $Executable
    $Shortcut.WorkingDirectory = Split-Path -Parent $Executable
    $Shortcut.Arguments = "--profile `"$Profile`""
    $Shortcut.Description = "WaterBuddy floating hydration pet"
    $Shortcut.Save()
}

if ($StartWithWindows) {
    $Startup = [Environment]::GetFolderPath("Startup")
    $StartupPath = Join-Path $Startup "WaterBuddy Pet.lnk"
    $StartupShortcut = $Shell.CreateShortcut($StartupPath)
    $StartupShortcut.TargetPath = $Executable
    $StartupShortcut.WorkingDirectory = Split-Path -Parent $Executable
    $StartupShortcut.Arguments = "--profile `"$Profile`""
    $StartupShortcut.Description = "WaterBuddy floating hydration pet"
    $StartupShortcut.Save()
}

Write-Host "Installed WaterBuddy Pet. Windows startup was $(if ($StartWithWindows) {'enabled'} else {'left off'})."
