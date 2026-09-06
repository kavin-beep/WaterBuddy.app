@echo off
setlocal
powershell.exe -NoProfile -Command "$shortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'WaterBuddy.lnk'; Remove-Item -LiteralPath $shortcut -Force -ErrorAction SilentlyContinue; Write-Host 'WaterBuddy Desktop shortcut removed.' -ForegroundColor Cyan"
pause
