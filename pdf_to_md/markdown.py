"""Build Markdown documents from per-page text and images."""

from __future__ import annotations


def build_markdown(
    text_pages: list[str],
    image_map: dict[int, list[str]] | None = None,
    *,
    title: str = "Converted PDF",
    image_dir_name: str = "",
) -> str:
    """Assemble markdown with optional page headings and image links."""
    image_map = image_map or {}
    parts: list[str] = [f"# {title}\n"]

    for i, text in enumerate(text_pages):
        parts.append(f"\n## Page {i + 1}\n")
        body = (text or "").strip()
        parts.append(body if body else "_(no text recovered)_")
        for img_name in image_map.get(i, []):
            rel = f"{image_dir_name}/{img_name}" if image_dir_name else img_name
            parts.append(f"\n![{img_name}]({rel})\n")

    return "\n".join(parts) + "\n"
