from pathlib import Path
from flask import Flask, render_template, request
from uuid import uuid4
from uploads import UPLOAD_ROOT, save_uploaded_image
from rapidocr import RapidOCR
from ocr import extract_text

app = Flask(__name__)

# Limit the total incoming request to 50 MiB for now.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

ocr_engine = None


def get_ocr_engine():
    """Initialize the OCR engine on its first use, then reuse it."""
    global ocr_engine

    if ocr_engine is None:
        ocr_engine = RapidOCR()

    return ocr_engine

@app.get("/")
def home():
    return render_template("index.html")


@app.post("/import")
def import_screenshots():
    uploaded_files = request.files.getlist("screenshots")

    image_files = [
        file
        for file in uploaded_files
        if file.filename
        and Path(file.filename).suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not image_files:
        return "No supported images found. Choose PNG or JPEG files.", 400

    import_folder = UPLOAD_ROOT / uuid4().hex

    results = []
    rejected_count = 0

    for uploaded_file in image_files:
        try:
            image_path = save_uploaded_image(uploaded_file, import_folder)
        except ValueError:
            rejected_count += 1
            continue

        lines = extract_text(image_path, get_ocr_engine())

        results.append({
            "filename": image_path.name,
            "line_count": len(lines),
        })

    return {
        "processed": len(results),
        "rejected": rejected_count,
        "results": results,
    }


if __name__ == "__main__":
    app.run(debug=True)