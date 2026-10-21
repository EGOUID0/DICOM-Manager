<!--
# DICOM-Manager - README
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09
-->

# DICOM-Manager

**Inspect, anonymize, modify, and organize DICOM files — from a desktop GUI or the command line.**

Developed by **Pascal Malouin (EGOUID0)**  
Repository: https://github.com/EGOUID0/DICOM-Manager/

DICOM-Manager is a cross-platform Python application for working with local DICOM datasets and file-sets. It provides a Qt desktop interface and a scriptable CLI built on a shared processing engine.

> **Medical-data warning:** DICOM files may contain protected patient information. Work on copies, verify outputs before sharing, and follow your organization's privacy requirements. The current anonymization command replaces a defined set of metadata fields; it is **not** a guarantee of complete DICOM de-identification. Other tags, private elements, burned-in annotations, and pixel data may still identify a patient.

## Features

- **Locate** DICOM instances in a directory tree.
- **Read and inspect** metadata using selected DICOM keywords; inspect in auto, multi-file, or per-file layouts.
- **Inspect file-sets** for DICOMDIR presence and DICOM File ID compatibility.
- **Anonymize** a restricted set of metadata fields using defaults, configuration files, and command-line overrides.
- **Modify** existing DICOM metadata using `--set` or configuration files.
- **Organize** files without rewriting their DICOM contents: preserve the source layout, flatten it, or generate a patient/study/series hierarchy.
- **Rename** instances, add `.dcm` extensions, and generate a DICOMDIR when file-set rules permit.
- **Create and edit templates** in TOML, JSON, or INI format.
- **Desktop GUI** with light/dark themes, configurable inspection fields, field editors, scope warnings, and saved preferences.

## Choose your installation method

| Method | Best for | Python required on target computer? |
| --- | --- | --- |
| **Windows portable ZIP** | Windows users who just want to run the application | **No** |
| **Install from source** | Linux, Windows, macOS developers and advanced users | **Yes, Python 3.12+** |
| **Build a distribution** | Maintainers producing portable executables | **Yes, on the build machine** |

## Requirements

For source installations, use **Python 3.12 or newer** and `pip`. The CLI requires `pydicom` and `rich`; the GUI additionally requires `PySide6`. A Git client is convenient but optional.

The Windows portable distribution bundles Python and its dependencies; users do **not** need to install Python.

## Windows: download and run the portable application

1. Open the [DICOM-Manager Releases page](https://github.com/EGOUID0/DICOM-Manager/releases).
2. Under the desired release's **Assets**, download the Windows portable ZIP (for example, `DICOM-Manager-2.0.0-Windows.zip`). The example name is illustrative; use the filename actually published.
3. In File Explorer, open **Downloads**, right-click the ZIP, choose **Extract All…**, choose a destination, and click **Extract**. **Do not run the executable from inside the ZIP.**
4. Open the extracted `DICOM-Manager-2.0.0-Windows` directory (the folder name may vary by release).
5. For the GUI, double-click `GUI\DICOM-Manager-GUI.exe`.
6. For the CLI, open PowerShell in the extracted directory and run:

```powershell
.\CLI\dicom-manager.exe --version
.\CLI\dicom-manager.exe --help
```

The extracted distribution should resemble:

```text
DICOM-Manager-2.0.0-Windows/
├── GUI/
│   ├── DICOM-Manager-GUI.exe
│   └── _internal/
├── CLI/
│   ├── dicom-manager.exe
│   └── _internal/
└── README-Windows.md
```

**Keep each executable together with its `_internal` directory.** You can move the complete extracted folder elsewhere, but don't move just the `.exe` file. If Windows displays a security warning, verify the file came from the project's official GitHub release before deciding whether to run it. Do not bypass organizational security policy.

There is no installer or automatic update service in the initial portable distribution. To upgrade, download and extract the newer release into a separate folder, test it, then retire the old folder.

## Install from source (CLI, GUI, or both)

### Step 1 — Obtain the source

**Using Git (recommended):**

```bash
git clone https://github.com/EGOUID0/DICOM-Manager.git
cd DICOM-Manager
```

**Without Git:** Visit the [repository](https://github.com/EGOUID0/DICOM-Manager/), choose **Code → Download ZIP**, extract it, and open a terminal in the extracted project directory (the one containing `pyproject.toml`). On Windows, use **Extract All…** in File Explorer. You can also download a source archive from a published GitHub release.

### Step 2 — Create a virtual environment

**Linux / macOS (Terminal):**

```bash
python3 --version             # Must be 3.12 or newer
python3 -m venv .venv
source .venv/bin/activate
```

If `python3` points to an older version, use an installed Python 3.12+ executable (for example `python3.12`) to create the environment.

**Windows (PowerShell):**

```powershell
py --version                  # Must be 3.12 or newer
py -m venv .venv
```

If the default Python is too old but Python 3.12 is installed, use `py -3.12 -m venv .venv`. The commands below use the environment's interpreter directly, so PowerShell activation is not required.

### Step 3 — Choose what to install

The GUI and CLI are **part of the same Python package**. Installing the GUI extra also installs the CLI; there is no separate GUI-only package.

**Linux / macOS (from the project directory):**

```bash
# CLI only
python -m pip install -e .

# OR CLI + GUI
python -m pip install -e '.[gui]'

# OR CLI + GUI + development/test tools
python -m pip install -e '.[gui,dev]'
```

These commands assume the virtual environment is activated (`source .venv/bin/activate`). Alternatively, use `.venv/bin/python -m pip ...` without activation.

**Windows (PowerShell, from the project directory):**

```powershell
# CLI only
.\.venv\Scripts\python.exe -m pip install -e .

# OR CLI + GUI
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"

# OR CLI + GUI + development/test tools
.\.venv\Scripts\python.exe -m pip install -e ".[gui,dev]"
```

Choose **one** of these install commands. `-e` means *editable install*: changes to the checked-out Python source are used without reinstalling the package.

### Step 4 — Run the application

**Linux / macOS (activated virtual environment):**

```bash
dicom-manager --version
dicom-manager --help
dicom-manager-gui               # GUI installations only
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\dicom-manager.exe --version
.\.venv\Scripts\dicom-manager.exe --help
.\.venv\Scripts\dicom-manager-gui.exe  # GUI installations only
```

If you only installed the CLI, `dicom-manager-gui` will not run until you install the GUI extra.

## Build distributable applications

### Windows (tested packaging workflow)

From the project root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build.ps1
```

The build script installs dependencies, runs tests unless `-SkipTests` is specified, builds GUI and CLI executables with PyInstaller, and produces a portable release ZIP under `release/`. Build on **Windows**: PyInstaller does not cross-compile Windows executables from Linux or macOS. Use a compatible Python 3.12+ interpreter and verify that the build script no longer hardcodes Python 3.12.

### macOS (experimental; not yet a tested release)

The shared Python core and PySide6 GUI are designed to be portable to macOS. You can try the **source installation** instructions above on a Mac, but a signed/notarized `.app` or `.dmg` has **not** been validated for this release.

**How to test without owning a Mac:** use a GitHub Actions workflow with a macOS runner to check out the repository, set up Python 3.12+, install `.[gui,dev]`, run `pytest`, and attempt a macOS PyInstaller build. The workflow can upload the resulting `.app` bundle as a test artifact. This provides automated build and basic launch verification, **not** a substitute for a person checking file dialogs, window behavior, display scaling, and DICOM workflows on macOS. Intel and Apple Silicon builds should be checked separately or via an explicitly tested universal build.

Do **not** publish the macOS artifact as a fully supported release until it has passed GUI testing on actual macOS. For frictionless public distribution, code signing and Apple notarization may also be required.

## GUI quick start

1. Select the **source directory** containing DICOM instances.
2. Open **Inspect** and choose the desired fields. Use **Auto**, **Multi-file**, or **Per-file** presentation.
3. Use **Inspect File-set** to see DICOMDIR and File ID compatibility in the main results panel.
4. Select **Anonymize**, **Modify**, or **Organize** and configure the output options.
5. Review the selected fields, values, and scope warning before running a modification.
6. Inspect the output directory and validate the results.

The GUI also supports editable TOML/JSON/INI configurations and remembers preferences through Qt's `QSettings`.

## CLI reference

```text
dicom-manager locate
dicom-manager read
dicom-manager inspect
dicom-manager anonymize
dicom-manager modify
dicom-manager organize
dicom-manager template
```

Use `dicom-manager COMMAND --help` for the authoritative option list for your installed version.

### Inspect metadata

```bash
dicom-manager inspect -d ./DICOM --fields PatientName PatientID AccessionNumber Modality
dicom-manager inspect -d ./DICOM --multi-file --fields PatientID StudyDescription
dicom-manager inspect -d ./DICOM --per-file --fields PatientID SeriesDescription
dicom-manager inspect -d ./DICOM --fileset
```

`--multi-file` uses files as rows and fields as columns. `--per-file` presents fields vertically for each instance. `--fileset` checks file-set compatibility.

### Anonymize

```bash
# Use built-in anonymization defaults
dicom-manager anonymize -d ./DICOM

# Override one default; other defaults still apply
dicom-manager anonymize -d ./DICOM --set PatientID=000123

# Combine a configuration file with a command-line override
dicom-manager anonymize -d ./DICOM --from-file anonymize.toml --set PatientID=000123
```

For anonymization, precedence is **built-in defaults → `--from-file` → `--set`**. Overrides are limited to the fields allowed by the anonymizer. Replacements may apply to matching tags within nested sequences as well as top-level attributes.

A single `--set PatientID=...` applies that value to the selected input batch. For distinct IDs across patients or batches, orchestrate separate runs and verify the patient/study scope. Do not assume that this command automatically allocates unique IDs.

### Modify

```bash
dicom-manager modify -d ./DICOM --set PatientName='EXAMPLE^PATIENT'
dicom-manager modify -d ./DICOM --set StudyDescription='Research Study'
```

**Scope matters:** if the source contains multiple patients, studies, or series, a field change may affect all matching instances. Review the GUI's scope warning or inspect the input first when using the CLI.

### Organize without modifying DICOM data

```bash
# Copy while preserving paths and filenames
dicom-manager organize -d ./DICOM

# Rename files while preserving directory structure
dicom-manager organize -d ./DICOM --rename

# Flatten into one output directory
dicom-manager organize -d ./DICOM --flat

# Generate PT/ST/SE/IM hierarchy
dicom-manager organize -d ./DICOM --hierarchical

# Add .dcm extensions for systems that require them
dicom-manager organize -d ./DICOM --hierarchical --dcm-extension

# Generate a DICOM file-set
dicom-manager organize -d ./DICOM --hierarchical --dicomdir

# Add a DICOMDIR to an already compliant source directory
dicom-manager organize -d ./DICOM --dicomdir --in-place
```

`organize` copies DICOM instances byte-for-byte; it reads metadata as necessary to determine destinations. The `--in-place` mode is deliberately restricted to adding DICOMDIR and must not be used to rename or rearrange source instances.

### Output layout and DICOMDIR rules

By default, processing creates a sibling directory such as `DICOM-anonymized`, `DICOM-modified`, or `DICOM-organized`. Use `-o` / `--output` to choose another destination.

| Option | Result |
| --- | --- |
| Default | Preserve source hierarchy and filenames |
| `--rename` | Generate `IMxxxxxx` filenames |
| `--flat` | Place instances in one directory with collision-safe generated names |
| `--hierarchical` | Generate `PTxxxxxx/STxxxxxx/SExxxxxx/IMxxxxxx` paths |
| `--dcm-extension` | Ensure `.dcm` extension |
| `--dicomdir` | Generate a DICOMDIR when the resulting File IDs are compliant |

`--dicomdir` and `--dcm-extension` **cannot be combined**: a DICOM File ID component cannot contain a period. Preserving arbitrary original directory names may also prevent DICOMDIR generation; use `--hierarchical --dicomdir` when needed.

### Templates

```bash
dicom-manager template --help
```

The GUI's **Templates** functionality can create, load, edit, and save TOML, JSON, and INI configuration files. Use the CLI help to check the exact template-generation arguments supported by your installed build.

## Development and testing

```bash
python -m pip install -e '.[gui,dev]'
python -m pytest -q
```

The processing core is shared by the CLI and GUI. The GUI must not implement a separate DICOM transformation engine.

## Roadmap

### 2.0 — Initial desktop release

- Cross-platform DICOM processing CLI
- PySide6 desktop GUI with dark/light themes
- File-set inspection and DICOMDIR creation
- Editable metadata/configuration workflows
- Windows portable packaging
- About dialog with project, developer, version, and dependency information

### 2.1 — Planned

- **Lazy-loaded field selectors:** show common fields immediately; search and load the full dictionary on demand.
- **Level-scoped modification:** select a patient, study, series, or individual instance before applying changes.
- Improved handling of mixed-patient and mixed-study inputs.

## Privacy and limitations

- Do not assume replacing a few demographic tags makes a dataset anonymous.
- Check private tags, nested sequences, free-text attributes, overlays, burned-in text, and pixel data before external disclosure.
- Use test or appropriately authorized datasets for development and support requests.
- DICOM-Manager is a metadata/file-set utility, not a diagnostic image viewer or a certified medical device.
- Validate exported DICOMDIR file-sets with the receiving system before relying on interoperability.

## License

DICOM-Manager is released under the **MIT License**. See [LICENSE](LICENSE) for the full terms.

Copyright (c) 2026 Pascal Malouin.

## Credits

**Developer:** Pascal Malouin (EGOUID0)  
**Repository:** https://github.com/EGOUID0/DICOM-Manager/  
**Core technologies:** Python, pydicom, Rich, PySide6 (Qt), PyInstaller.
