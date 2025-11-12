# app.py — minimal & robust Flask server
import os, csv, json, re
from flask import Flask, jsonify, make_response, send_from_directory
from flask_cors import CORS # Make sure this import is here

app = Flask(__name__)
CORS(app) # <-- THIS LINE IS CRITICAL

# ----- Resolve CSV path safely (works no matter where you run from)
HERE = os.path.dirname(os.path.abspath(__file__))          # ...\backend
ROOT = os.path.abspath(os.path.join(HERE, ".."))           # project root
CANDIDATES = [
    os.environ.get("PRODUCTS_CSV"),                        # optional override
    os.path.join(HERE, "products.csv"),                    # backend/products.csv
    os.path.join(ROOT, "products.csv"),                    # root/products.csv
    os.path.join(ROOT, "products - Copy.csv"),             # root/products - Copy.csv
]
CSV_PATH = next((p for p in CANDIDATES if p and os.path.exists(p)), None)

# ---- Cleaning helpers ----
_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def strip_citations(s: str) -> str:
    # remove patterns like:  [cite: 7]
    return re.sub(r"\s*\[cite:\s*[^]]+\]\s*", "", s or "")

def normalize_digits(s: str) -> str:
    return (s or "").translate(_ARABIC_INDIC)

def clean_price(raw: str) -> float:
    """
    Accept '7.25', '7,25', ' 7.25 [cite: 7]', '٧٫٢٥', 'USD 7.25', etc.
    Extracts the first numeric token and converts comma to dot.
    """
    s = normalize_digits(strip_citations(str(raw))).strip()
    m = re.search(r"[-+]?\d+(?:[.,]\d+)?", s)
    if not m:
        return 0.0
    return float(m.group(0).replace(",", "."))

# ----- Routes -----
@app.get("/health")
def health():
    return {"ok": True, "csv": CSV_PATH or "NOT FOUND"}

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.get("/products")
def products():
    try:
        if not CSV_PATH:
            raise FileNotFoundError(f"No CSV found in {CANDIDATES}")

        rows = []
        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            if not r.fieldnames:
                raise ValueError("CSV has no headers.")
            for row in r:
                # Clean all string fields (remove [cite: ...])
                for k, v in list(row.items()):
                    if isinstance(v, str):
                        row[k] = strip_citations(v).strip()
                # Robust price parsing
                row["price (جملة الجملة (دولار))"] = clean_price(
                    row.get("price (جملة الجملة (دولار))", "")
                )
                rows.append(row)

        return jsonify(rows)
    except Exception as e:
        return make_response((f"/products failed: {e}", 500))

@app.get("/test")
def test_route():
    return "The new code is working!"

if __name__ == "__main__":
    # Run in debug so you see tracebacks if anything goes wrong
    app.run(host="0.0.0.0", port=5000, debug=True)

