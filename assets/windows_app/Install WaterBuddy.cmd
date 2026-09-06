@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-WaterBuddy.ps1"
if errorlevel 1 (
  echo.
  echo WaterBuddy could not create the Desktop shortcut.
  pause
)
