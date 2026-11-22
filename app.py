from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

# Limit the total incoming request to 50 MiB for now.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


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

    return f"Received {len(image_files)} supported image(s)."


if __name__ == "__main__":
    app.run(debug=True)