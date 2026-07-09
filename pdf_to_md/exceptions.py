"""Domain errors for pdf_to_md."""


class PdfToMdError(Exception):
    """Base error for this package."""


class MissingDependencyError(PdfToMdError):
    """A required optional dependency or system binary is missing."""


class ConversionError(PdfToMdError):
    """PDF conversion failed."""
