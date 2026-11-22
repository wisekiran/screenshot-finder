from pathlib import Path

from rapidocr import RapidOCR

from ocr import extract_text

from storage import (
    initialize_database,
    is_screenshot_unchanged,
    save_screenshot,
)

from fingerprints import calculate_file_hash


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

    initialize_database()
    engine = RapidOCR()

    for image_path in image_paths:
        print(f"\n--- {image_path.name} ---")

        try:
            file_hash = calculate_file_hash(image_path)

            if is_screenshot_unchanged(image_path, file_hash):
                print("Unchanged—skipping OCR.")
                continue

            lines = extract_text(image_path, engine)
            save_screenshot(image_path, lines, file_hash)
        except Exception as error:
            print(f"Could not process or save this image: {error}")
            continue

        print("Saved to database.")

        if lines:
            print("\n".join(lines))
        else:
            print("No text was detected.")


if __name__ == "__main__":
    main()
