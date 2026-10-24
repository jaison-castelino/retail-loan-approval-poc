"""Policy and Eligibility Agent. Fictional bank policy; clause retrieval by keyword overlap; rules are plain Python.
Thresholds are ILLUSTRATIVE bank settings, not RBI or universal rules."""
import re
T = dict(min_age=21, max_age=60, min_years=2, income_multiple=12, score_fail=680, score_refer=720, foir_fail=50, foir_refer=40)
POLICY_NAME = "Fictional Bank Policy"
STOP = set("a an the of to or and in on at for is are be must not by as than with any".split())

def clauses():
    t = T
    return [
        dict(id="PL-1.1", title="Applicant age", text=f"Applicants must be aged {t['min_age']} to {t['max_age']} years at application. Age outside this range is a policy exception."),
        dict(id="PL-1.2", title="Employment continuity", text=f"Applicants should have at least {t['min_years']} years of total employment. A shorter history is a policy exception."),
        dict(id="PL-2.1", title="Bureau credit score", text=f"A credit bureau score below {t['score_fail']} is a decline recommendation. A score from {t['score_fail']} to {t['score_refer'] - 1} requires manual credit officer review."),
        dict(id="PL-2.2", title="Fixed obligations to income ratio", text=f"Fixed obligations to income ratio (existing EMIs plus proposed EMI, divided by gross monthly income) above {t['foir_fail']}% is a decline recommendation. Above {t['foir_refer']}% requires manual review."),
        dict(id="PL-2.3", title="Loan size", text=f"The requested amount must not exceed {t['income_multiple']} times gross monthly income."),
        dict(id="PL-3.1", title="Mandatory documents", text="PAN, salary slip and bank statement are mandatory. Missing documents require further information before the assessment can complete."),
        dict(id="PL-3.2", title="Name consistency", text="The applicant name must match across the application and identity records. A mismatch requires manual review for possible fraud or data error."),
        dict(id="PL-4.1", title="Escalation", text="Any exception, conflict or unresolved concern must be escalated to a human credit officer. AI output is a recommendation and not a sanction."),
    ]

def _tok(s): return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP}

def retrieve(query):
    """Return the best-matching clause using simple keyword overlap (title words count double). No vector database."""
    q = _tok(query)
    return max(clauses(), key=lambda c: 2 * len(q & _tok(c["title"])) + len(q & _tok(c["text"])))

QUERIES = {"age": "applicant age range years", "employment": "years of employment continuity", "score": "credit bureau score decline review",
           "foir": "fixed obligations to income ratio EMI", "loan": "loan size requested amount cap",
           "docs": "mandatory documents missing", "name": "name mismatch identity records"}

def evaluate(a, foir, missing, name_match):
    t = T; out = []
    def add(key, check, result, detail, evidence):
        c = retrieve(QUERIES[key])
        out.append(dict(check=check, clause_id=c["id"], clause_text=c["text"], result=result, detail=detail, evidence=evidence,
                        source="Deterministic rule + keyword clause retrieval", agent="Policy Agent"))
    ok = t["min_age"] <= a["age"] <= t["max_age"]
    add("age", "Age", "Pass" if ok else "Fail", "Within range" if ok else "Outside permitted range", f"Age {a['age']}")
    ok = a["years"] >= t["min_years"]
    add("employment", "Employment", "Pass" if ok else "Fail", "Meets minimum" if ok else "Below minimum", f"{a['years']} years")
    s = a["score"]; r = "Fail" if s < t["score_fail"] else "Refer" if s < t["score_refer"] else "Pass"
    add("score", "Bureau score", r, {"Fail": "Below decline threshold", "Refer": "In manual-review band", "Pass": "Above review band"}[r], f"Mock bureau score {s}")
    r = "Fail" if foir > t["foir_fail"] else "Refer" if foir > t["foir_refer"] else "Pass"
    add("foir", "FOIR", r, {"Fail": "Above decline threshold", "Refer": "In manual-review band", "Pass": "Within comfort range"}[r], f"FOIR {foir:.1f}% after new EMI")
    ok = a["amount"] <= a["income"] * t["income_multiple"]
    add("loan", "Loan size", "Pass" if ok else "Fail", "Within cap" if ok else "Exceeds cap", f"Amount {a['amount']:,} vs income {a['income']:,}/month")
    add("docs", "Documents", "Pass" if not missing else "Refer", "Complete" if not missing else "Missing: " + ", ".join(missing), f"Received {len(a['docs'])} of 3")
    add("name", "Name consistency", "Pass" if name_match else "Refer", "Consistent" if name_match else "Mismatch with PAN record", f"Form '{a['name']}' vs PAN '{a['pan_name']}'")
    return out
