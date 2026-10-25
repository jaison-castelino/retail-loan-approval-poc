"""Builds all synthetic tables (as lists of row dicts) for CSV export and BigQuery."""
import agents, mocks, policy, synth

REQUIRED = ["PAN", "Salary slip", "Bank statement"]
APPLICANT_KEYS = (
"id", "name", "age", "income", "emi", "amount", "tenure", "score", "docs", "pan_name", "years", "scenario")
NAMES = ["applicants", "loan_applications", "customer_accounts", "transactions", "existing_loans", "repayment_history",
         "bureau_results", "document_findings", "policy_rules", "agent_logs", "decisions", "audit_events"]


def build_tables(apps):
    t = {n: [] for n in NAMES}
    for a in apps:
        prof = synth.local_profile(a);
        out = agents.run_agents(a, prof, synth.SOURCE)
        t["applicants"].append({k: a[k] for k in APPLICANT_KEYS})
        t["loan_applications"].append(
            dict(application_id=a["id"], applicant_id=a["id"], requested_amount=a["amount"], tenure_months=a["tenure"],
                 purpose="Personal use", submitted_on="2026-09-30", recommendation=out["rec"]))
        t["customer_accounts"] += synth.accounts_for(a);
        t["transactions"] += synth.transactions_for(a)
        t["existing_loans"] += prof["loans"];
        t["repayment_history"] += prof["repayments"]
        b = mocks.bureau(a);
        d = b["data"]
        t["bureau_results"].append(
            dict(applicant_id=a["id"], status=b["status"], score=d.get("score"), enquiries_6m=d.get("enquiries_6m"),
                 active_loans=d.get("active_loans"), note=b["note"], latency_ms=b["latency_ms"]))
        for doc in REQUIRED:
            t["document_findings"].append(
                dict(applicant_id=a["id"], doc_type=doc, status="Received" if doc in a["docs"] else "Missing",
                     source="Simulated (pre-generated findings)"))
        t["document_findings"].append(
            dict(applicant_id=a["id"], doc_type="PAN name check", status=mocks.pan_verify(a)["status"],
                 source="Simulated API (mock PAN)"))
        for i, r in enumerate(out["log"], 1):
            t["agent_logs"].append(
                dict(application_id=a["id"], seq=i, agent=r["Agent"], action=r["Action"], evidence=r["Evidence"],
                     outcome=r["Outcome"], source=r["Source"], timestamp=r["Timestamp"]))
    t["policy_rules"] = [dict(clause_id=c["id"], title=c["title"], text=c["text"]) for c in policy.clauses()]
    return t
