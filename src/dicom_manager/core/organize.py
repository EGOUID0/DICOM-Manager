# DICOM-Manager - Organize.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

"""Filesystem-only DICOM organization.

Existing DICOM instance bytes are copied unchanged. pydicom is used only to read
metadata required to calculate a hierarchical destination.
"""
from pathlib import Path
import shutil
import pydicom

from .discovery import locate_dicom_files
from .output import HierarchyState, RenameState, destination_for, prepare_output


def organize(source: Path, output: Path, mode: str, overwrite: bool = False,
             rename: bool = False, dcm_extension: bool = False) -> int:
    files = locate_dicom_files(source)
    if not files:
        raise ValueError(f"No DICOM files found under {source}")
    prepare_output(output, overwrite=overwrite)
    hierarchy = HierarchyState()
    rename_state = RenameState()
    destinations: set[Path] = set()

    # Flattening requires generated names: preserving basenames can collide.
    effective_rename = rename or mode in {"flat", "hierarchical"}

    for index, src in enumerate(files, 1):
        # Only hierarchy calculation requires DICOM metadata. No dataset is saved.
        ds = pydicom.dcmread(src, stop_before_pixels=True) if mode == "hierarchical" else None
        dst = destination_for(
            src, source, output, mode, ds, hierarchy, rename_state, index,
            rename=effective_rename, dcm_extension=dcm_extension,
        )
        if dst in destinations or dst.exists():
            raise ValueError(f"Output filename collision: {dst}. Use --rename or --hierarchical.")
        destinations.add(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return len(files)
