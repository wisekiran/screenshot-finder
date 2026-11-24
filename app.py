from pathlib import Path
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from uuid import uuid4
from uploads import UPLOAD_ROOT, save_uploaded_image
from rapidocr import RapidOCR
from ocr import extract_text
import os
import secrets
from fingerprints import calculate_file_hash
from storage import (
    find_screenshot_by_hash,
    initialize_database,
    save_screenshot,
    search_screenshots,
    get_screenshot_path,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("Set the SECRET_KEY environment variable before starting Flask.")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

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

def get_collection_id() -> str:
    """Get or create the current browser session's collection."""
    if "collection_id" not in session:
        session["collection_id"] = uuid4().hex

    return session["collection_id"]

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
        return render_template(
            "error.html",
            title="No evidence found.",
            message="Choose a folder containing PNG or JPEG screenshots.",
        ), 400

    initialize_database()

    collection_id = get_collection_id()
    import_folder = UPLOAD_ROOT / collection_id / uuid4().hex

    results = []
    rejected_count = 0
    duplicate_count = 0

    for uploaded_file in image_files:
        try:
            image_path = save_uploaded_image(uploaded_file, import_folder)
        except ValueError:
            rejected_count += 1
            continue

        file_hash = calculate_file_hash(image_path)

        existing_id = find_screenshot_by_hash(
            file_hash,
            collection_id,
        )

        if existing_id is not None:
            image_path.unlink()
            duplicate_count += 1
            continue

        try:
            lines = extract_text(image_path, get_ocr_engine())
        except Exception:
            image_path.unlink(missing_ok=True)
            app.logger.exception("OCR failed during screenshot import")
            abort(500)

        save_screenshot(
            image_path,
            lines,
            file_hash,
            collection_id=collection_id,
        )

        results.append({
            "filename": image_path.name,
            "line_count": len(lines),
        })

    session["last_import"] = {
        "processed": len(results),
        "duplicates_skipped": duplicate_count,
        "rejected": rejected_count,
    }

    return redirect(url_for("import_complete"), code=303)

@app.get("/search")
def search():
    initialize_database()

    query = request.args.get("q", "").strip()
    matches = search_screenshots(query, get_collection_id())

    screenshot_ids = [
        screenshot_id
        for screenshot_id, _ in matches
    ]

    return render_template(
        "results.html",
        query=query,
        screenshot_ids=screenshot_ids,
    )

@app.get("/screenshots/<int:screenshot_id>")
def screenshot_image(screenshot_id: int):
    image_path = get_screenshot_path(
        screenshot_id,
        get_collection_id(),
    )

    if image_path is None or not image_path.is_file():
        abort(404)

    response = send_file(image_path, conditional=False)
    response.headers["Cache-Control"] = "private, no-store"
    return response

@app.get("/import/complete")
def import_complete():
    summary = session.get("last_import")

    if summary is None:
        return redirect(url_for("home"))

    return render_template(
        "import_result.html",
        processed=summary["processed"],
        duplicates_skipped=summary["duplicates_skipped"],
        rejected=summary["rejected"],
    )

@app.errorhandler(413)
def upload_too_large(error):
    return render_template(
        "error.html",
        title="Too much evidence.",
        message=(
            "This import exceeds the 50 MiB limit. "
            "Split your screenshots into smaller folders and try again."
        ),
    ), 413


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html",
        title="The trail went cold.",
        message=(
            "This page or screenshot isn’t available in your collection."
        ),
    ), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template(
        "error.html",
        title="Something didn’t click.",
        message=(
            "We couldn’t finish that request. Some screenshots may already "
            "have been indexed. You can search your collection or retry "
            "the import; existing duplicates will be skipped."
        ),
    ), 500


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")