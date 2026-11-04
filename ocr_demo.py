from pathlib import Path

from rapidocr import RapidOCR

image_path = Path(__file__).parent / "data" / "sample.png"

if not image_path.is_file():
    raise FileNotFoundError(f"Screenshot not found: {image_path}")

engine = RapidOCR()
result = engine(str(image_path))

if result.txts:
    for text in result.txts:
        print(text)
else:
    print("No text found in the image.")