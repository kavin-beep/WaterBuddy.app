$ErrorActionPreference = "Stop"

$AppUrl = "https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/"
$InstallDirectory = Join-Path $env:LOCALAPPDATA "WaterBuddy"
$DesktopDirectory = [Environment]::GetFolderPath("Desktop")
$IconSource = Join-Path $PSScriptRoot "WaterBuddy.ico"
$IconTarget = Join-Path $InstallDirectory "WaterBuddy.ico"
$ShortcutPath = Join-Path $DesktopDirectory "WaterBuddy.lnk"

New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
Copy-Item -LiteralPath $IconSource -Destination $IconTarget -Force

$ChromeCandidates = @(
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)},
    $env:LOCALAPPDATA
) | Where-Object { $_ } | ForEach-Object {
    Join-Path $_ "Google\Chrome\Application\chrome.exe"
}
$Chrome = $ChromeCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
if ($Chrome) {
    $Shortcut.TargetPath = $Chrome
    $Shortcut.Arguments = "--app=$AppUrl"
    $Shortcut.WorkingDirectory = Split-Path -Parent $Chrome
} else {
    $Shortcut.TargetPath = Join-Path $env:SystemRoot "System32\rundll32.exe"
    $Shortcut.Arguments = "url.dll,FileProtocolHandler $AppUrl"
}
$Shortcut.IconLocation = "$IconTarget,0"
$Shortcut.Description = "Open WaterBuddy"
$Shortcut.Save()

Write-Host "WaterBuddy was added to your Windows Desktop." -ForegroundColor Cyan
Write-Host "You can now double-click the WaterBuddy icon to open the app."
Read-Host "Press Enter to close"
