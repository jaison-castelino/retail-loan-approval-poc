"""Agent orchestration and validation of agent outputs. No Streamlit imports, so it is testable and reusable by scripts."""
import datetime as dt, math, re
import mocks, policy, synth
from logic import emi_calc

RATE = 11.5
RESULTS = {"Pass", "Refer", "Fail"}
RECS = {"Recommend APPROVE", "REFER - request documents", "REFER - manual review", "Recommend DECLINE"}
AUTHORITIES = {"Branch credit officer", "Regional credit manager", "Zonal credit committee"}
FINDING_KEYS = ("check", "clause_id", "clause_text", "result", "detail", "evidence", "source", "agent")
LOG_KEYS = ("Agent", "Action", "Evidence", "Outcome", "Source", "Timestamp")


class AgentOutputError(ValueError):
    """Raised when an agent returns output that does not match the expected structure."""


def ts(): return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_finding(f):
    for k in FINDING_KEYS:
        if not isinstance(f.get(k), str) or not f[k].strip(): raise AgentOutputError(f"finding is missing '{k}'")
    if f["result"] not in RESULTS: raise AgentOutputError(f"invalid result '{f['result']}'")
    if not re.fullmatch(r"PL-\d+\.\d+", f["clause_id"]): raise AgentOutputError(f"invalid clause id '{f['clause_id']}'")


def validate_log_row(r):
    for k in LOG_KEYS:
        if not isinstance(r.get(k), str) or not r[k].strip(): raise AgentOutputError(f"log row is missing '{k}'")


def validate_output(o):
    if o.get("rec") not in RECS: raise AgentOutputError(f"invalid recommendation '{o.get('rec')}'")
    if not isinstance(o.get("foir"), (int, float)) or not math.isfinite(o["foir"]) or o[
        "foir"] < 0: raise AgentOutputError("invalid FOIR")
    if o.get("authority") not in AUTHORITIES: raise AgentOutputError("invalid approval authority")
    if not o.get("findings"): raise AgentOutputError("no policy findings returned")
    for f in o["findings"]: validate_finding(f)
    for r in o.get("log", []): validate_log_row(r)


def credit_assess(profile, source):
    loans, reps = profile["loans"], profile["repayments"]
    late = [r for r in reps if r["days_past_due"] > 0]
    return dict(total_emi=sum(l["monthly_emi"] for l in loans), n_loans=len(loans), late_count=len(late),
                max_dpd=max([r["days_past_due"] for r in reps], default=0), source=source)


def run_agents(a, profile=None, source=None):
    if profile is None: profile, source = synth.local_profile(a), synth.SOURCE
    log, flags = [], []

    def step(agent, action, evidence, outcome, src="Deterministic rule"):
        log.append(dict(Agent=agent, Action=action, Evidence=evidence, Outcome=outcome, Source=src, Timestamp=ts()))

    ext = {"bureau": mocks.bureau(a), "pan": mocks.pan_verify(a), "bank": mocks.bank_verify(a),
           "fraud": mocks.fraud_screen(a)}
    dfind = a.get("doc_findings")
    missing = sorted({"PAN", "Salary slip", "Bank statement"} - set(a["docs"]))
    dsrc = "Document extraction (pypdf)" if dfind else "Simulated (pre-generated findings)"
    step("Document Agent", "Check mandatory documents", f"Received: {', '.join(a['docs'])}",
         "Complete" if not missing else "Missing: " + ", ".join(missing), dsrc)
    for d in dfind or []:
        step("Document Agent", f"Read {d['doc']}",
             "No readable text" if d["unreadable"] else f"Name '{d['name']}', income {d['income']}",
             "Unreadable" if d["unreadable"] else "Extracted", "Document extraction (pypdf)")
    p = ext["pan"];
    match = p["status"] == "verified"
    step("Document Agent", "Cross-check applicant name with PAN record", f"Form: {a['name']} | {p['note']}",
         "Match" if match else "Conflict", "Simulated API (mock PAN)")
    b = ext["bureau"]
    if b["status"] == "ok":
        sc = b["data"]["score"]
        step("Credit Agent", "Fetch bureau report", f"Score {sc}, enquiries (6m) {b['data']['enquiries_6m']}",
             "Good" if sc >= 720 else "Fair" if sc >= 680 else "Weak", "Simulated API (mock bureau)")
    else:
        step("Credit Agent", "Fetch bureau report", b["note"], "Unavailable: cannot assess, refer",
             "Simulated API (mock bureau)")
    credit = credit_assess(profile, source)
    step("Credit Agent", "Review existing loan accounts",
         f"{credit['n_loans']} account(s), total EMI {credit['total_emi']:,}",
         "Matches declared EMI" if credit["total_emi"] == a["emi"] else f"Differs from declared EMI {a['emi']:,}",
         credit["source"])
    step("Credit Agent", "Review 12-month repayment history",
         f"{credit['late_count']} late payment(s), worst {credit['max_dpd']} days past due",
         "No adverse indicators" if credit["late_count"] == 0 else "Adverse repayment indicator", credit["source"])
    for k in ("bank", "fraud"):
        step("Risk Agent", ext[k]["service"], ext[k]["note"], ext[k]["status"].capitalize(), "Simulated API (mock)")
    new_emi = emi_calc(a["amount"], a["tenure"])
    foir = (credit["total_emi"] + new_emi) / a["income"] * 100
    step("Affordability Agent", "Compute FOIR after new EMI",
         f"Existing EMI {credit['total_emi']:,}, new EMI {new_emi:,.0f}, income {a['income']:,}",
         f"FOIR {foir:.1f}% (policy cap {policy.T['foir_fail']}%)")
    findings = policy.evaluate(a, foir, missing, match, ext, dfind, credit)
    for f in findings:
        step("Policy Agent", f"{f['check']} - clause {f['clause_id']}", f["evidence"], f"{f['result']}: {f['detail']}",
             f["source"])
    fails = [f for f in findings if f["result"] == "Fail"];
    refers = [f for f in findings if f["result"] == "Refer"]
    flags += [f"Clause {f['clause_id']} ({f['check']}): {f['detail']}" for f in fails + refers]
    if fails:
        rec = "Recommend DECLINE"
    elif missing:
        rec = "REFER - request documents"
    elif refers:
        rec = "REFER - manual review"
    else:
        rec = "Recommend APPROVE"
    step("Recommendation Agent", "Assemble evidence-based recommendation", f"{len(flags)} flag(s); FOIR {foir:.1f}%",
         rec)
    out = dict(log=log, flags=flags, rec=rec, foir=foir, new_emi=new_emi, findings=findings, ext=ext,
               authority=policy.authority(a["amount"]), credit=credit, profile=profile, validated=True)
    try:
        validate_output(out)
    except AgentOutputError as e:  # invalid agent output is never trusted: escalate to a person
        out["rec"] = "REFER - manual review";
        out["validated"] = False
        out["flags"].append(f"Agent output failed validation: {e}")
    return out
