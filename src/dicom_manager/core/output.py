# DICOM-Manager - Output.
# Author: Pascal Malouin (https://github.com/EGOUID0)
# Project: https://github.com/EGOUID0/DICOM-Manager
# Created: 2026-10-09

from dataclasses import dataclass, field
from pathlib import Path
import shutil

@dataclass
class HierarchyState:
    patients: dict[str, int] = field(default_factory=dict)
    studies: dict[tuple[str, str], int] = field(default_factory=dict)
    series: dict[tuple[str, str, str], int] = field(default_factory=dict)
    images: dict[tuple[str, str, str], int] = field(default_factory=dict)

    @staticmethod
    def _sibling_index(mapping, key, parent_prefix):
        if key not in mapping:
            mapping[key] = sum(1 for k in mapping if k[:-1] == parent_prefix)
        return mapping[key]

    def destination(self, root: Path, ds, dcm_extension: bool = False) -> Path:
        patient = str(getattr(ds, 'PatientID', '') or getattr(ds, 'PatientName', '') or 'UNKNOWN')
        study = str(getattr(ds, 'StudyInstanceUID', '') or 'UNKNOWN')
        series = str(getattr(ds, 'SeriesInstanceUID', '') or 'UNKNOWN')

        if patient not in self.patients:
            self.patients[patient] = len(self.patients)
        p = self.patients[patient]
        s = self._sibling_index(self.studies, (patient, study), (patient,))
        se = self._sibling_index(self.series, (patient, study, series), (patient, study))
        key = (patient, study, series)
        im = self.images.get(key, 0)
        self.images[key] = im + 1
        name = f'IM{im:06d}' + ('.dcm' if dcm_extension else '')
        return root / f'PT{p:06d}' / f'ST{s:06d}' / f'SE{se:06d}' / name


@dataclass
class RenameState:
    counters: dict[Path, int] = field(default_factory=dict)

    def name(self, parent: Path, dcm_extension: bool) -> str:
        index = self.counters.get(parent, 0)
        self.counters[parent] = index + 1
        return f'IM{index:06d}' + ('.dcm' if dcm_extension else '')


def default_output(source: Path, command: str) -> Path:
    suffix = {'anonymize': '-anonymized', 'modify': '-modified', 'organize': '-organized'}[command]
    return source.parent / f'{source.name}{suffix}'


def prepare_output(path: Path, overwrite: bool = False) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(f'Output already exists: {path} (use --overwrite)')
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _with_dcm_extension(name: str) -> str:
    return name if name.lower().endswith('.dcm') else f'{name}.dcm'


def destination_for(source_file: Path, source_root: Path, output_root: Path, mode: str,
                    dataset, hierarchy: HierarchyState, rename_state: RenameState,
                    flat_index: int, rename: bool = False,
                    dcm_extension: bool = False) -> Path:
    if mode == 'hierarchical':
        return hierarchy.destination(output_root, dataset, dcm_extension=dcm_extension)

    if mode == 'flat':
        parent = output_root
        if rename:
            name = rename_state.name(Path('.'), dcm_extension)
        else:
            name = source_file.name
            if dcm_extension:
                name = _with_dcm_extension(name)
        return parent / name

    rel = source_file.relative_to(source_root)
    parent = output_root / rel.parent
    if rename:
        name = rename_state.name(rel.parent, dcm_extension)
    else:
        name = rel.name
        if dcm_extension:
            name = _with_dcm_extension(name)
    return parent / name
