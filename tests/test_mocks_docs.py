import os, sys, io

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import mocks, docreader, data


class F:
    def __init__(self, p): self.name = os.path.basename(p); self._d = open(p, "rb").read()

    def getvalue(self): return self._d


def demo(i): return next(a for a in data.DEMO_APPS if a["id"] == i)


def test_mock_scenarios():
    assert mocks.bureau(demo("PL-1001"))["status"] == "ok"
    assert mocks.bureau(demo("PL-1008"))["status"] == "unavailable"
    assert mocks.fraud_screen(demo("PL-1007"))["status"] == "flagged"
    assert mocks.pan_verify(demo("PL-1005"))["status"] == "inconsistent"
    assert all(mocks.fraud_screen(demo("PL-1001"))["label"].startswith("MOCK") for _ in (0,))


def test_pdf_reading():
    root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples")
    docs, f = docreader.analyse(
        [F(os.path.join(root, n)) for n in ("salary_slip_ananya.pdf", "bank_statement_ananya.pdf", "pan_ananya.pdf")])
    assert docs == ["Salary slip", "Bank statement", "PAN"]
    assert f[0]["income"] == 95000 and f[0]["name"] == "Ananya Rao" and not f[0]["unreadable"]
