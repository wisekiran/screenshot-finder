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

## Development setup

Requires Python 3.11.

Create a virtual environment:

    python -m venv .venv

Activate it in Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

## Local data

Private screenshots and generated data belong in the data/ folder,
which is excluded from Git.