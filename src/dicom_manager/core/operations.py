# DICOM-Manager - Operation.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from pathlib import Path
import pydicom
from .dataset import apply_values
from .discovery import locate_dicom_files
from .output import HierarchyState, RenameState, destination_for, prepare_output


def transform(source: Path, output: Path, values: dict[str, str], mode: str,
              overwrite: bool = False, rename: bool = False,
              dcm_extension: bool = False) -> tuple[int, dict[str, int]]:
    files = locate_dicom_files(source)
    if not files:
        raise ValueError(f'No DICOM files found under {source}')
    prepare_output(output, overwrite=overwrite)
    hierarchy = HierarchyState()
    rename_state = RenameState()
    totals = {key: 0 for key in values}
    destinations: set[Path] = set()
    for index, src in enumerate(files, 1):
        ds = pydicom.dcmread(src)
        counts = apply_values(ds, values)
        for key, count in counts.items():
            totals[key] += count
        dst = destination_for(
            src, source, output, mode, ds, hierarchy, rename_state, index,
            rename=rename, dcm_extension=dcm_extension,
        )
        if dst in destinations or dst.exists():
            raise ValueError(
                f'Output filename collision: {dst}. Use --rename or --hierarchical.'
            )
        destinations.add(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(dst)
    return len(files), totals
