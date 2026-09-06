param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EntryPoint = Join-Path $PSScriptRoot "waterbuddy_pet.py"

& $Python -m pip install -r (Join-Path $ProjectRoot "desktop-requirements.txt")
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "WaterBuddyPet" `
    --paths $ProjectRoot `
    --distpath (Join-Path $ProjectRoot "dist") `
    --workpath (Join-Path $ProjectRoot "build\waterbuddy-pet") `
    --specpath (Join-Path $ProjectRoot "build") `
    $EntryPoint

Write-Host "Built: $(Join-Path $ProjectRoot 'dist\WaterBuddyPet.exe')"
