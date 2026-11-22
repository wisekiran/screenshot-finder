# Screenshot Finder

Find saved screenshots using information you remember about them.

## Goal

Build a searchable screenshot library, starting with text extraction
and keyword search.

## Current status

Extracts text from a local screenshot using RapidOCR and ONNX Runtime.
Search and the web interface are not implemented yet.

## Run the OCR demo

Install dependencies in your activated virtual environment:

    python -m pip install -r requirements.txt

Place a PNG screenshot at data/sample.png, then run:

    python ocr_demo.py

Recognized text is printed in the terminal.

## Scan multiple screenshots

Place PNG or JPEG screenshots directly inside data/, then run:

    python scan_folder.py

The scanner prints each filename and its extracted text.
If an image fails, it reports the error and continues with the others.

## Local storage

The folder scanner saves extracted text and absolute image paths
in data/screenshots.db using SQLite.

Scanning the same file path again updates its text and indexing time.
Identical images at different paths are not yet deduplicated.

The database and screenshots are excluded from Git.

## Search screenshots

After scanning your screenshots, run:

    python search.py

Enter a word or phrase to search the saved OCR text.
Search ignores English letter case and returns matching image paths.
Empty queries are rejected.

This currently performs literal substring matching, not semantic search.

## Skip unchanged screenshots

The scanner stores a SHA-256 fingerprint for each image.
If the same file path has the same fingerprint on a later scan,
OCR is skipped.

New or changed files are processed and saved.
Identical files at different paths are still stored separately.

## Development setup

Requires Python 3.11.

Create a virtual environment:

    python -m venv .venv

Activate it in Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

## Local data

Private screenshots and generated data belong in the data/ folder,
which is excluded from Git.

## Local web interface

Start the development server:

python app.py

Open http://127.0.0.1:5000 in your browser.

Choose a folder containing PNG or JPEG screenshots, then click
"Import screenshots". Folder selection includes subfolders.

The app validates and saves supported images, extracts their text,
and returns a JSON summary. Web imports are not yet connected
to database storage or search.

Uploads are stored locally in data/uploads and excluded from Git.
The total upload request is currently limited to 50 MiB.

## Run tests

From the project folder, run:

    python -m unittest discover -s tests -v

Tests cover file fingerprints and database updates.
They use temporary files and a temporary database,
without modifying your personal screenshots or database.