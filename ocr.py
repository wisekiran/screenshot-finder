from pathlib import Path

from rapidocr import RapidOCR


def extract_text(image_path: Path, engine: RapidOCR) -> list[str]:
    """Extract text lines from an image."""
    if not image_path.is_file():
        raise FileNotFoundError(f"Screenshot not found: {image_path}")

    result = engine(str(image_path))

    if result.txts is None:
        return []

    return list(result.txts)