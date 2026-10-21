from dicom_manager.core.config import load_values, write_template


def test_template_roundtrip(tmp_path):
    expected = {"PatientName": "ANONYMOUS", "PatientID": "ABC"}
    for suffix in ("toml", "json", "ini"):
        path = tmp_path / f"values.{suffix}"
        write_template(path, expected)
        assert load_values(path) == expected
