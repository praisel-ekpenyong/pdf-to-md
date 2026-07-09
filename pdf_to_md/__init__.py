"""PDF to Markdown conversion with hybrid OCR support."""

from pdf_to_md.converter import (
    ConvertOptions,
    ConvertResult,
    convert_bytes,
    convert_file,
)
from pdf_to_md.deps import (
    DependencyReport,
    format_dependency_issues,
    probe_dependencies,
)
from pdf_to_md.exceptions import (
    ConversionError,
    MissingDependencyError,
    PdfToMdError,
)

__all__ = [
    "ConvertOptions",
    "ConvertResult",
    "ConversionError",
    "DependencyReport",
    "MissingDependencyError",
    "PdfToMdError",
    "convert_bytes",
    "convert_file",
    "format_dependency_issues",
    "probe_dependencies",
]

__version__ = "0.1.0"
