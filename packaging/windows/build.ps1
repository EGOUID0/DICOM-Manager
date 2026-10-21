# DICOM-Manager - Windows release builder.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

param([switch]$SkipTests)

$ErrorActionPreference = 'Stop'

Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path

Set-Location $root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py) not found. Install Python 3.12 or newer.'
}

& py -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw 'DICOM-Manager requires Python 3.12 or newer.'
}

$PythonVersion = & py -c "import platform; print(platform.python_version())"
Write-Host "Default Python: $PythonVersion"

if (-not (Test-Path '.venv/Scripts/python.exe')) {
    & py -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create Python virtual environment.' 
    }
}

$python = Join-Path $root '.venv/Scripts/python.exe'
& $python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw 'Existing virtual environment uses Python older than 3.12. Remove .venv and rebuild.'
}

$VenvVersion = & $python -c "import platform; print(platform.python_version())"
Write-Host "Build environment Python: $VenvVersion"

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw 'pip upgrade failed'
}

& $python -m pip install -e '.[gui,dev]' 'pyinstaller>=6,<7'
if ($LASTEXITCODE -ne 0) {
    throw 'Dependency install failed'
}

if (-not $SkipTests) {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Tests failed; packaging aborted'
    }
}

& $python -m PyInstaller --noconfirm --clean --onedir --windowed --name DICOM-Manager-GUI --collect-all pydicom --collect-all rich packaging/windows/gui_entry.py
if ($LASTEXITCODE -ne 0) {
    throw 'GUI build failed'
}

& $python -m PyInstaller --noconfirm --clean --onedir --console --name dicom-manager --collect-all pydicom --collect-all rich packaging/windows/cli_entry.py
if ($LASTEXITCODE -ne 0) {
    throw 'CLI build failed'
}

& (Join-Path $root 'dist/dicom-manager/dicom-manager.exe') --version
if ($LASTEXITCODE -ne 0) {
    throw 'CLI smoke test failed'
}

& (Join-Path $root 'dist/dicom-manager/dicom-manager.exe') --help | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'CLI help smoke test failed'
}

$release = Join-Path $root 'release/DICOM-Manager-2.0.0a7-Windows'
if (Test-Path $release) {
    Remove-Item -Recurse -Force $release
}

New-Item -ItemType Directory -Force -Path $release | Out-Null

Copy-Item -Recurse -Force 'dist/DICOM-Manager-GUI' (Join-Path $release 'GUI')
Copy-Item -Recurse -Force 'dist/dicom-manager' (Join-Path $release 'CLI')
Copy-Item -Force 'packaging/windows/README-Windows.md' (Join-Path $release 'README-Windows.md')

$zip = Join-Path $root 'release/DICOM-Manager-2.0.0a7-Windows.zip'
if (Test-Path $zip) {
    Remove-Item $zip
}
Compress-Archive -Path $release -DestinationPath $zip
Write-Host "Built Windows distribution: $zip"

Write-Host 'GUI: GUI/DICOM-Manager-GUI.exe; CLI: CLI/dicom-manager.exe'
