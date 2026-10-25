"""Policy and Eligibility Agent. Clauses live in policy_docs/*.txt (fictional, illustrative; not RBI rules).
Retrieval is keyword overlap; checks are plain Python."""
import os, re, glob
T = dict(min_age=21, max_age=60, min_years=2, income_multiple=12, score_fail=680, score_refer=720, foir_fail=50, foir_refer=40, auth_1=300000, auth_2=1000000, dpd_refer=30, dpd_fail=90)
POLICY_NAME = "Fictional Bank Policy"
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policy_docs")
STOP = set("a an the of to or and in on at for is are be must not by as than with any".split())
SRC_RULE = "Deterministic rule + keyword clause retrieval"

DEFAULT_CLAUSES = {
    "PL-1.1": ("Applicant age", "Applicants must be aged {min_age} to {max_age} years at application. Age outside this range is a policy exception."),
    "PL-1.2": ("Employment continuity", "Applicants should have at least {min_years} years of total employment. A shorter history is a policy exception."),
    "PL-2.1": ("Bureau credit score", "A credit bureau score below {score_fail} is a decline recommendation. A score from {score_fail} to {score_refer_m1} requires manual credit officer review."),
    "PL-2.2": ("Fixed obligations to income ratio", "Fixed obligations to income ratio (existing EMIs plus proposed EMI, divided by gross monthly income) above {foir_fail}% is a decline recommendation. Above {foir_refer}% requires manual review."),
    "PL-2.3": ("Loan size", "The requested amount must not exceed {income_multiple} times gross monthly income."),
    "PL-2.4": ("Repayment history", "A payment more than {dpd_refer} days past due in the last 12 months requires manual review. A payment more than {dpd_fail} days past due in the last 12 months is a decline recommendation."),
    "PL-3.1": ("Mandatory documents", "PAN, salary slip and bank statement are mandatory and must be readable. Missing or unreadable documents require further information before the assessment can complete."),
    "PL-3.2": ("Name consistency", "The applicant name must match across the application and identity records. A mismatch requires manual review for possible fraud or data error."),
    "PL-3.3": ("External verification", "Results from external verification services that are unavailable, inconsistent or adverse require manual review. Services: credit bureau, bank account verification and fraud screening."),
    "PL-3.4": ("Income evidence", "Income stated in the application must be supported by the salary slip. A difference of more than 10% requires manual review."),
    "PL-4.1": ("Escalation", "Any exception, conflict or unresolved concern must be escalated to a human credit officer. AI output is a recommendation and not a sanction."),
    "PL-4.2": ("Approval authority", "Approval authority depends on the requested amount: up to INR {auth_1:,} the branch credit officer, up to INR {auth_2:,} the regional credit manager, above that the zonal credit committee."),
}

def _read_clauses():
    """Read policy_docs/*.txt (first line 'ID | Title', then text). If the folder is missing or empty, use the built-in copy."""
    raw = []
    for p in sorted(glob.glob(os.path.join(DIR, "*.txt"))):
        head, _, body = open(p, encoding="utf-8").read().partition("\n")
        cid, title = [x.strip() for x in head.split("|", 1)]
        raw.append((cid, title, body))
    if not raw:
        raw = [(k, t, b) for k, (t, b) in DEFAULT_CLAUSES.items()]
    out = [dict(id=c, title=t, text=" ".join(b.split()).format(score_refer_m1=T["score_refer"] - 1, **T)) for c, t, b in raw]
    for c in out: c["_t"], c["_x"] = _tok(c["title"]), _tok(c["text"])   # precomputed tokens for fast retrieval
    return out

_CLAUSES, _RET = {}, {}

def clauses():
    """Clauses for the current thresholds, cached so files are read once per threshold setting."""
    key = tuple(sorted(T.items()))
    if key not in _CLAUSES:
        _CLAUSES.clear(); _RET.clear(); _CLAUSES[key] = _read_clauses()
    return _CLAUSES[key]

def _tok(s): return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP}

def retrieve(query):
    cl = clauses(); key = (id(cl), query)
    if key not in _RET:
        q = _tok(query)
        _RET[key] = max(cl, key=lambda c: 2 * len(q & c["_t"]) + len(q & c["_x"]))
    return _RET[key]

def authority(amount):
    return "Branch credit officer" if amount <= T["auth_1"] else "Regional credit manager" if amount <= T["auth_2"] else "Zonal credit committee"

QUERIES = {"age": "applicant age range years", "employment": "years of employment continuity", "score": "credit bureau score decline review",
           "foir": "fixed obligations to income ratio EMI", "loan": "loan size requested amount cap", "docs": "mandatory documents missing",
           "name": "name mismatch identity records", "external": "external verification services unavailable adverse",
           "income": "income evidence salary slip difference", "repayment": "repayment history days past due late payments"}

def evaluate(a, foir, missing, name_match, ext=None, dfind=None, credit=None):
    t = T; out = []; ext = ext or {}
    def add(key, check, result, detail, evidence, source=SRC_RULE):
        c = retrieve(QUERIES[key])
        out.append(dict(check=check, clause_id=c["id"], clause_text=c["text"], result=result, detail=detail, evidence=evidence, source=source, agent="Policy Agent"))
    ok = t["min_age"] <= a["age"] <= t["max_age"]
    add("age", "Age", "Pass" if ok else "Fail", "Within range" if ok else "Outside permitted range", f"Age {a['age']}")
    ok = a["years"] >= t["min_years"]
    add("employment", "Employment", "Pass" if ok else "Fail", "Meets minimum" if ok else "Below minimum", f"{a['years']} years")
    bu = ext.get("bureau")
    if bu and bu["status"] != "ok":
        add("score", "Bureau score", "Refer", "Bureau unavailable; score cannot be assessed", f"Mock bureau: {bu['status']}", "Simulated API + rule")
    else:
        s = a["score"]; r = "Fail" if s < t["score_fail"] else "Refer" if s < t["score_refer"] else "Pass"
        add("score", "Bureau score", r, {"Fail": "Below decline threshold", "Refer": "In manual-review band", "Pass": "Above review band"}[r], f"Mock bureau score {s}", "Simulated API (mock bureau) + rule")
    r = "Fail" if foir > t["foir_fail"] else "Refer" if foir > t["foir_refer"] else "Pass"
    add("foir", "FOIR", r, {"Fail": "Above decline threshold", "Refer": "In manual-review band", "Pass": "Within comfort range"}[r], f"FOIR {foir:.1f}% after new EMI")
    ok = a["amount"] <= a["income"] * t["income_multiple"]
    add("loan", "Loan size", "Pass" if ok else "Fail", "Within cap" if ok else "Exceeds cap", f"Amount {a['amount']:,} vs income {a['income']:,}/month")
    add("docs", "Documents", "Pass" if not missing else "Refer", "Complete" if not missing else "Missing: " + ", ".join(missing), f"Received {len(a['docs'])} of 3")
    add("name", "Name consistency", "Pass" if name_match else "Refer", "Consistent" if name_match else "Mismatch with PAN record", f"Form '{a['name']}' vs PAN '{a['pan_name']}'", "Simulated API (mock PAN) + rule")
    for key, label in (("bank", "Bank account verification"), ("fraud", "Fraud screening")):
        if key in ext:
            ok = ext[key]["status"] in ("verified", "clear")
            add("external", label, "Pass" if ok else "Refer", ext[key]["note"], f"Mock status: {ext[key]['status']}", "Simulated API + rule")
    for d in dfind or []:
        if d.get("unreadable"):
            add("docs", "Document readability", "Refer", f"{d['doc']} has no readable text", "pypdf found no text", "Document extraction (pypdf) + rule")
    inc = [d["income"] for d in dfind or [] if d.get("income")]
    if inc:
        diff = abs(inc[0] - a["income"]) / a["income"] * 100
        add("income", "Income evidence", "Pass" if diff <= 10 else "Refer", f"Difference {diff:.0f}%", f"Slip {inc[0]:,} vs stated {a['income']:,}", "Document extraction (pypdf) + rule")
    names = [d["name"] for d in dfind or [] if d.get("name")]
    if names:
        bad = [n for n in names if n.lower() != a["name"].lower()]
        add("name", "Document name match", "Pass" if not bad else "Refer", "Consistent" if not bad else f"Differs: {bad[0]}", f"Names read: {', '.join(names)}", "Document extraction (pypdf) + rule")
    if credit is not None:
        m = credit["max_dpd"]; r = "Fail" if m >= t["dpd_fail"] else "Refer" if m >= t["dpd_refer"] else "Pass"
        add("repayment", "Repayment history", r, {"Fail": "Severe delinquency in last 12 months", "Refer": "Late payment in last 12 months", "Pass": "No late payments in last 12 months"}[r],
            f"{credit['late_count']} late payment(s), worst {m} days past due across {credit['n_loans']} account(s)", credit["source"] + " + rule")
    return out
