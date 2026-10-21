# DICOM-Manager - Fileset handler.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from dataclasses import dataclass
from pathlib import Path

import pydicom
from pydicom.filebase import DicomFileLike
from pydicom.fileset import FileSet, is_conformant_file_id

from .discovery import locate_dicom_files


@dataclass(frozen=True)
class FileSetReport:
    files: int
    dicomdir_present: bool
    compliant: bool
    invalid_directories: tuple[Path, ...]
    invalid_files: tuple[Path, ...]


def inspect_fileset(root: Path) -> FileSetReport:
    files = locate_dicom_files(root)
    bad_dirs: set[Path] = set()
    bad_files: list[Path] = []
    for path in files:
        rel = path.relative_to(root)
        if not is_conformant_file_id(rel):
            bad_files.append(rel)
        for parent in rel.parents:
            if parent == Path('.'):
                continue
            # Validate the directory path independently; a bad filename should not
            # make an otherwise valid directory appear invalid.
            if not is_conformant_file_id(parent):
                bad_dirs.add(parent)
    return FileSetReport(
        files=len(files),
        dicomdir_present=(root / 'DICOMDIR').is_file(),
        compliant=not bad_files,
        invalid_directories=tuple(sorted(bad_dirs, key=str)),
        invalid_files=tuple(sorted(bad_files, key=str)),
    )


def create_dicomdir(root: Path) -> Path:
    """Create DICOMDIR for files already stored below *root*.

    pydicom's public FileSet.write() deliberately reorganizes a new File-set.
    DICOM-Manager must not do that: layout is selected independently by the user.
    We therefore use FileSet.add() to build pydicom's standards-aware directory
    record tree, replace each leaf's ReferencedFileID with the actual compliant
    path, then use pydicom's DICOMDIR encoder without moving the instances.

    The final call is intentionally isolated here because _write_dicomdir() is a
    private pydicom API. Tests should catch upstream changes.
    """
    report = inspect_fileset(root)
    if not report.files:
        raise ValueError(f'No DICOM files found under {root}')
    if not report.compliant:
        examples = '\n'.join(f'  {p}' for p in report.invalid_files[:5])
        more = '' if len(report.invalid_files) <= 5 else f'\n  ... and {len(report.invalid_files)-5} more'
        raise ValueError(
            'Cannot create DICOMDIR: output contains non-conformant DICOM File IDs.\n'
            f'{examples}{more}\nUse --rename and/or --hierarchical.'
        )

    fs = FileSet()
    for path in locate_dicom_files(root):
        instance = fs.add(path)
        rel = path.relative_to(root)
        instance.node._record.ReferencedFileID = list(rel.parts)

    # Set the root so the generated DICOMDIR represents this existing File-set.
    fs._root_path = root
    target = root / 'DICOMDIR'
    with target.open('wb') as raw:
        fp = DicomFileLike(raw)
        fs._write_dicomdir(fp)

    # Validate that pydicom can load what we just wrote and resolve every instance.
    check = FileSet(target)
    if len(check) != report.files:
        target.unlink(missing_ok=True)
        raise ValueError(
            f'DICOMDIR validation failed: expected {report.files} instances, found {len(check)}'
        )
    return target
