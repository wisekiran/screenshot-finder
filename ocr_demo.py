from pathlib import Path

from rapidocr import RapidOCR

from ocr import extract_text


def main() -> None:
    image_path = Path(__file__).parent / "data" / "sample.png"
    engine = RapidOCR()
    lines = extract_text(image_path, engine)

    if lines:
        for line in lines:
            print(line)
    else:
        print("No text was detected.")


if __name__ == "__main__":
    main()