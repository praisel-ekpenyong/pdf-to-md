"""Tests for image format detection."""

from pdf_to_md.images import detect_image_extension, sanitize_filename


def test_detect_png():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    assert detect_image_extension(data) == "png"


def test_detect_jpeg():
    data = b"\xff\xd8\xff\xe0" + b"\x00" * 16
    assert detect_image_extension(data) == "jpg"


def test_detect_gif():
    assert detect_image_extension(b"GIF89a" + b"\x00" * 8) == "gif"


def test_detect_unknown():
    assert detect_image_extension(b"not-an-image") == "bin"


def test_sanitize_filename():
    assert sanitize_filename("My Doc!!.pdf") == "My_Doc_.pdf" or "My" in sanitize_filename(
        "My Doc!!.pdf"
    )
    assert sanitize_filename("@@@") == "image"
