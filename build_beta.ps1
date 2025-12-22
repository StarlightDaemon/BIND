$ErrorActionPreference = "Stop"

Write-Host "Setting up Virtual Environment (venv)..."
if (Test-Path "venv") {
    Write-Host "Removing existing venv..."
    Remove-Item "venv" -Recurse -Force
}
python -m venv venv

# Define paths to venv executables
$VENV_PYTHON = ".\venv\Scripts\python.exe"
$VENV_PIP = ".\venv\Scripts\pip.exe"

Write-Host "Upgrading pip..."
& $VENV_PYTHON -m pip install --upgrade pip

Write-Host "Installing Dependencies into venv..."
& $VENV_PIP install -r requirements.txt
& $VENV_PIP install pyinstaller

Write-Host "Cleaning previous builds..."
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "abmg.spec") { Remove-Item "abmg.spec" -Force }

Write-Host "Building ABMG Beta GUI..."
# Run PyInstaller from the venv, pointing to root GUI file
# --noconsole: Hide the black terminal window
& $VENV_PYTHON -m PyInstaller --onefile --clean --noconsole --name abmg_gui `
    --hidden-import=click `
    --hidden-import=schedule `
    --hidden-import=cloudscraper `
    --hidden-import=bs4 `
    --hidden-import=qbittorrentapi `
    abmg_gui.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build Successful!" -ForegroundColor Green
    Write-Host "Executable located at: dist\abmg_gui.exe"
}
else {
    Write-Host "Build Failed!" -ForegroundColor Red
    exit 1
}
