from pathlib import Path
from types import SimpleNamespace
from dicom_manager.core.output import HierarchyState, RenameState, default_output, destination_for


def ds(patient="P1", study="1.2.3", series="1.2.3.4"):
    return SimpleNamespace(PatientID=patient, PatientName="", StudyInstanceUID=study, SeriesInstanceUID=series)


def test_hierarchical_is_dicom_fileset_style(tmp_path):
    h = HierarchyState(); r = RenameState()
    out = destination_for(Path("/src/a"), Path("/src"), tmp_path, "hierarchical", ds(), h, r, 1)
    assert out.relative_to(tmp_path) == Path("PT000000/ST000000/SE000000/IM000000")


def test_preserve_rename_keeps_directory(tmp_path):
    h = HierarchyState(); r = RenameState()
    out = destination_for(Path("/src/A/B/whatever"), Path("/src"), tmp_path, "preserve", ds(), h, r, 1, rename=True)
    assert out.relative_to(tmp_path) == Path("A/B/IM000000")


def test_dcm_extension(tmp_path):
    h = HierarchyState(); r = RenameState()
    out = destination_for(Path("/src/A/image"), Path("/src"), tmp_path, "preserve", ds(), h, r, 1, dcm_extension=True)
    assert out.name == "image.dcm"


def test_organize_default_output():
    assert default_output(Path("/tmp/study"), "organize") == Path("/tmp/study-organized")
