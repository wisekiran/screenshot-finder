from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage


UPLOAD_ROOT = Path(__file__).parent / "data" / "uploads"

SUPPORTED_FORMATS = {
    "PNG": ".png",
    "JPEG": ".jpg",
}


def save_uploaded_image(upload: FileStorage, folder: Path) -> Path:
    """Validate an uploaded image and save it with a generated filename."""
    try:
        with Image.open(upload.stream) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise ValueError("This file is not a valid supported image.") from error

    if image_format not in SUPPORTED_FORMATS:
        raise ValueError("Only PNG and JPEG images are supported.")

    folder.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{SUPPORTED_FORMATS[image_format]}"
    destination = folder / filename

    upload.stream.seek(0)
    upload.save(destination)

    return destination