"""Deterministic synthetic credit profile data: accounts, transactions, existing loans, repayment history."""
import random

MONTHS = [f"{2025 + (9 + i) // 12}-{(9 + i) % 12 + 1:02d}" for i in range(12)]  # 2025-10 .. 2026-09
SOURCE = "Synthetic (local generator)"
LOAN_TYPES = ["Personal loan", "Auto loan", "Credit card EMI", "Two-wheeler loan", "Consumer durable loan"]
FORCED_DPD = {"PL-1003": 90, "PL-1004": 30}  # reliable demo cases


def _r(a, tag): return random.Random(f"{a['id']}|{tag}")


def loans_for(a):
    emi = a["emi"]
    if emi <= 0: return []
    r = _r(a, "loans");
    n = 1 if emi < 4000 else r.choice([1, 2])
    first = int(emi * r.uniform(0.3, 0.7) // 100 * 100) or emi // 2
    parts = [emi] if n == 1 else [first, emi - first]
    return [
        dict(loan_id=f"{a['id']}-L{i + 1}", applicant_id=a["id"], loan_type=r.choice(LOAN_TYPES), monthly_emi=int(p),
             outstanding=int(p * r.randint(6, 36)), remaining_months=r.randint(6, 36)) for i, p in enumerate(parts)]


def repayments_for(a, loans):
    r = _r(a, "rep");
    p = max(0, 720 - a["score"]) / 2000;
    rows = []
    for l in loans:
        for m in MONTHS:
            dpd = (r.choice([30, 30, 60, 90]) if a["score"] < 650 else 30) if r.random() < p else 0
            rows.append(dict(loan_id=l["loan_id"], applicant_id=a["id"], month=m, days_past_due=dpd,
                             status="On time" if dpd == 0 else "Late"))
    if a["id"] in FORCED_DPD and rows: rows[3]["days_past_due"] = FORCED_DPD[a["id"]]; rows[3]["status"] = "Late"
    return rows


def accounts_for(a):
    r = _r(a, "acct")
    return [dict(account_id=f"{a['id']}-AC1", applicant_id=a["id"], account_type="Salary account",
                 avg_balance=int(a["income"] * r.uniform(0.5, 3)), years_open=r.randint(1, 12))]


def transactions_for(a):
    r = _r(a, "txn");
    rows = [];
    acct = f"{a['id']}-AC1"
    for m in MONTHS[-6:]:
        rows.append(
            dict(txn_id=f"{a['id']}-{m}-S", applicant_id=a["id"], account_id=acct, month=m, txn_type="Salary credit",
                 amount=int(a["income"] * r.uniform(0.97, 1.0))))
        if a["emi"] > 0: rows.append(
            dict(txn_id=f"{a['id']}-{m}-E", applicant_id=a["id"], account_id=acct, month=m, txn_type="EMI debit",
                 amount=a["emi"]))
        if a["score"] < 640 and r.random() < 0.3: rows.append(
            dict(txn_id=f"{a['id']}-{m}-B", applicant_id=a["id"], account_id=acct, month=m, txn_type="Bounced debit",
                 amount=0))
    return rows


def local_profile(a):
    loans = loans_for(a)
    return dict(loans=loans, repayments=repayments_for(a, loans))
