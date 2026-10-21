<!--
# DICOM-Manager - Windows release README
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09
-->

# DICOM-Manager 2.0.0a7 — Windows

## Build requirements

- Windows 10/11 x64
- Python 3.12 x64, installed with the Python launcher `py`
- PowerShell and internet access to install dependencies

From the extracted project directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build.ps1
```

The script creates `release/DICOM-Manager-2.0.0a7-Windows.zip` containing:

- `GUI/DICOM-Manager-GUI.exe` (desktop app; keep `_internal` alongside it)
- `CLI/dicom-manager.exe` (command-line app; keep `_internal` alongside it)

These are **portable one-folder distributions**, not a signed Windows installer. They are built separately to avoid fragile shared-PyInstaller-runtime handling. The CLI executable can be called from PowerShell using its full path or by adding the `CLI` directory to `PATH`.

## Validation on Windows

```powershell
.\release\DICOM-Manager-2.0.0a7-Windows\CLI\dicom-manager.exe --version
.\release\DICOM-Manager-2.0.0a7-Windows\CLI\dicom-manager.exe --help
.\release\DICOM-Manager-2.0.0a7-Windows\GUI\DICOM-Manager-GUI.exe
```

Then test `inspect`, `organize`, `anonymize --set`, DICOMDIR, light/dark themes and settings persistence with **non-identifying test DICOM files**. Confirm the packaged application works on a clean Windows machine without Python installed. Do not distribute actual patient data or test output containing PHI.

## Notes

- PyInstaller is not a cross-compiler: run this build on Windows.
- The PowerShell script runs pytest before packaging unless `-SkipTests` is passed.
- This does not create an MSI/MSIX or code-sign the binaries; these are subsequent release tasks.
- The script requires Python 3.12 specifically; adapt the `py -3.12` line if targeting another supported interpreter.
