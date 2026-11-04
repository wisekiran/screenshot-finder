from pathlib import Path

from rapidocr import RapidOCR

from ocr import extract_text


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

def main() -> None:
    folder = Path(__file__).parent / "data"

    image_paths =sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not image_paths:
        print("No supported images found.")
        return

    engine = RapidOCR()

    for image_path in image_paths:
        print(f"\n--- {image_path.name} ---")

        try:
            lines = extract_text(image_path, engine)
        except Exception as error:
            print(f"Could not process this image: {error}")
            continue

        if lines:
            print("\n".join(lines))
        else:
            print("No text was detected.")


if __name__ == "__main__":
    main()
