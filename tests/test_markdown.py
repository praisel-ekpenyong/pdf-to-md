"""Markdown builder unit tests."""

from pdf_to_md.markdown import build_markdown


def test_build_markdown_pages():
    md = build_markdown(["Hello", ""], title="Demo")
    assert "# Demo" in md
    assert "## Page 1" in md
    assert "Hello" in md
    assert "## Page 2" in md
    assert "no text extracted" in md


def test_build_markdown_images():
    md = build_markdown(
        ["x"],
        {0: ["fig.png"]},
        title="T",
        image_dir_name="out_images",
    )
    assert "![fig.png](out_images/fig.png)" in md
