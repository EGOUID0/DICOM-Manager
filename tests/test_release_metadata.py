from pathlib import Path
import tomllib
from dicom_manager import __version__


def test_release_metadata():
    root = Path(__file__).resolve().parents[1]
    meta = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["version"] == __version__
    assert meta["project"]["requires-python"] == ">=3.12"
    assert (root / "LICENSE").is_file()


def test_about_dialog_is_available():
    root = Path(__file__).resolve().parents[1]
    gui = (root / "src/dicom_manager/gui.py").read_text(encoding="utf-8")
    assert "def show_about(self):" in gui
    assert "Pascal Malouin (EGOUID0)" in gui
    assert "https://github.com/EGOUID0/DICOM-Manager/" in gui
