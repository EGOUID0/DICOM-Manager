# DICOM-Manager - Discovery.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from pathlib import Path
import pydicom


def is_dicom(path: Path) -> bool:
    if not path.is_file() or path.name.upper() == "DICOMDIR":
        return False
    try:
        pydicom.dcmread(path, stop_before_pixels=True, force=False, specific_tags=[])
        return True
    except Exception:
        return False


def locate_dicom_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if is_dicom(p))


def locate_dicomdirs(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file() and p.name.upper() == "DICOMDIR")
