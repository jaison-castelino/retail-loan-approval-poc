"""Reads text-based PDFs with pypdf and extracts a name and monthly income. Scanned PDFs need OCR (not built)."""
import io, re


def _text(data):
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages).strip()
    except Exception:
        return ""


def classify(text, fname):
    t = (text + " " + fname).lower()
    if "salary" in t: return "Salary slip"
    if "statement" in t: return "Bank statement"
    if re.search(r"\bpan\b|permanent account", t): return "PAN"
    return "Unknown"


def extract(text):
    n = re.search(r"(?:Employee Name|Account Holder|Name)\s*:\s*(.+)", text)
    i = re.search(r"Net Monthly Salary\s*:\s*INR\s*([\d,]+)", text)
    return (n.group(1).strip() if n else None), (int(i.group(1).replace(",", "")) if i else None)


def analyse(files):
    docs, finds = [], []
    for f in files:
        text = _text(f.getvalue());
        doc = classify(text, f.name);
        name, income = extract(text)
        docs.append(doc);
        finds.append(dict(doc=doc, name=name, income=income, unreadable=not text))
    return docs, finds
