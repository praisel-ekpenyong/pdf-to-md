"""poppler path helpers."""

from pathlib import Path

from pdf_to_md.deps import DependencyReport, poppler_bin_dir


def test_poppler_bin_dir_from_exe_string():
    # Path may not exist on disk; Path.parent still works
    p = str(Path("C:/tools/poppler/Library/bin/pdftoppm.exe"))
    d = poppler_bin_dir(p)
    assert d is not None
    assert d.replace("\\", "/").endswith("bin")


def test_report_poppler_bin_dir_property():
    report = DependencyReport(
        digital_extract_available=True,
        ocr_python_packages=True,
        tesseract_available=True,
        poppler_available=True,
        poppler_path=r"C:\poppler\Library\bin\pdftoppm.exe",
        ocr_ready=True,
    )
    assert report.poppler_bin_dir is not None
    assert "bin" in report.poppler_bin_dir.replace("\\", "/")
