"""Create synthetic sample PDFs in samples/ (needs: pip install reportlab)."""
from reportlab.pdfgen import canvas


def pdf(fn, lines):
    c = canvas.Canvas(f"samples/{fn}");
    y = 800
    for l in lines: c.drawString(60, y, l); y -= 24
    c.save()


pdf("salary_slip_ananya.pdf",
    ["SALARY SLIP (SAMPLE, SYNTHETIC)", "Employee Name: Ananya Rao", "Net Monthly Salary: INR 95,000"])
pdf("salary_slip_ananya_mismatch.pdf",
    ["SALARY SLIP (SAMPLE, SYNTHETIC)", "Employee Name: Ananya Rao", "Net Monthly Salary: INR 60,000"])
pdf("bank_statement_ananya.pdf",
    ["BANK STATEMENT (SAMPLE, SYNTHETIC)", "Account Holder: Ananya Rao", "Average monthly credits: INR 95,000"])
pdf("pan_ananya.pdf", ["PAN CARD (SAMPLE, SYNTHETIC)", "Name: Ananya Rao", "PAN: XXXXX0000X"])
