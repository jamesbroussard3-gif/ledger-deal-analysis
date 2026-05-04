"""
Flask web application for Ledger — Deal Analysis tool.

Routes:
  GET  /               -> Render the main page
  POST /analyze        -> Accept input (text/PDF/spreadsheet), return analysis
  POST /chat           -> Follow-up Q&A on a completed analysis
  POST /memo/docx      -> Download analysis as a Word memo
  POST /memo/pdf       -> Download analysis as a PDF memo
"""

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

# Load .env before importing modules that rely on the API key
load_dotenv()

from analyzer import chat_followup, run_full_analysis
from memo_generator import generate_docx, generate_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap


def parse_pdf(file_storage) -> str:
    """Extract text from a PDF upload."""
    from pypdf import PdfReader

    reader = PdfReader(file_storage)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts)


def parse_spreadsheet(file_storage, filename: str) -> str:
    """Flatten an Excel/CSV into a text representation the LLM can read."""
    import pandas as pd

    if filename.lower().endswith(".csv"):
        df = pd.read_csv(file_storage)
        return df.to_string(index=False)

    excel = pd.ExcelFile(file_storage)
    parts = []
    for sheet_name in excel.sheet_names:
        df = excel.parse(sheet_name)
        parts.append(f"=== Sheet: {sheet_name} ===\n{df.to_string(index=False)}")
    return "\n\n".join(parts)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        input_type = request.form.get("input_type", "text")

        if input_type == "text":
            raw_text = request.form.get("text", "").strip()
            if not raw_text:
                return jsonify({"error": "No text provided."}), 400

        elif input_type == "pdf":
            file = request.files.get("file")
            if not file or not file.filename:
                return jsonify({"error": "No PDF file uploaded."}), 400
            raw_text = parse_pdf(file.stream)

        elif input_type == "spreadsheet":
            file = request.files.get("file")
            if not file or not file.filename:
                return jsonify({"error": "No spreadsheet uploaded."}), 400
            raw_text = parse_spreadsheet(file.stream, file.filename)

        else:
            return jsonify({"error": f"Unknown input type: {input_type}"}), 400

        if not raw_text.strip():
            return jsonify({"error": "Could not extract any text from the input."}), 400

        result = run_full_analysis(raw_text)
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        context = data.get("context", {})
        conversation = data.get("conversation", [])
        if not conversation:
            return jsonify({"error": "No conversation provided."}), 400
        reply = chat_followup(context, conversation)
        return jsonify({"reply": reply})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500


def _safe_filename(company_name: str, ext: str) -> str:
    """Build a safe download filename from a company name."""
    name = company_name or "target"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60]
    return f"Deal_Memo_{safe}.{ext}"


@app.route("/memo/docx", methods=["POST"])
def memo_docx():
    try:
        analysis = request.get_json()
        if not analysis:
            return jsonify({"error": "No analysis data provided."}), 400

        company = (analysis.get("extracted_data") or {}).get("company_name") or "target"
        filename = _safe_filename(company, "docx")

        docx_bytes = generate_docx(analysis)
        return Response(
            docx_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Memo generation failed: {str(e)}"}), 500


@app.route("/memo/pdf", methods=["POST"])
def memo_pdf():
    try:
        analysis = request.get_json()
        if not analysis:
            return jsonify({"error": "No analysis data provided."}), 400

        company = (analysis.get("extracted_data") or {}).get("company_name") or "target"
        filename = _safe_filename(company, "pdf")

        pdf_bytes = generate_pdf(analysis)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Memo generation failed: {str(e)}"}), 500


if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        print("\n" + "=" * 60)
        print("ERROR: GEMINI_API_KEY is not set.")
        print("Create a .env file in this directory containing:")
        print("GEMINI_API_KEY=your-key-here")
        print("Get a free key at: https://aistudio.google.com/apikey")
        print("=" * 60 + "\n")
        exit(1)

    print("\n" + "=" * 60)
    print("Ledger — Deal Analysis is starting...")
    print("Open http://127.0.0.1:5000 in your browser")
    print("Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5000)
