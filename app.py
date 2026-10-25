"""Agentic AI Loan Approval Workbench - PROOF OF CONCEPT (synthetic data only).
Run: pip install streamlit pandas plotly ; streamlit run app.py
Fictional Bank (not a real bank). No real bureau/Aadhaar/PAN/RBI calls are made."""
import datetime as dt
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Fict Bank - Loan Workbench (PoC)", layout="wide")
RATE = 11.5  # indicative annual rate, synthetic

# ---------- Synthetic, deterministic scenarios ----------
from logic import emi_calc
import data
import policy
import mocks
import docreader
from agents import run_agents

def ts():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------- Agents (deterministic rules; no LLM needed) ----------
@st.cache_data(show_spinner=False, ttl=300)
def _load_apps():
    return data.load_applicants()
APPS, DATA_SOURCE = _load_apps()
@st.cache_data(show_spinner=False, ttl=300)
def _load_profiles():
    apps, _ = data.load_applicants()
    return data.load_profiles(apps)
PROFILES, PROFILE_SOURCE = _load_profiles()

if "decisions" not in st.session_state:
    (st.session_state.decisions, st.session_state.audit,
     st.session_state.accepted, st.session_state.disbursed) = data.load_state()
    st.session_state.extra = []

def all_apps():
    return APPS + st.session_state.extra

def status(a):
    d = st.session_state.decisions.get(a["id"])
    if d: return d["decision"]
    return "Flagged" if a["rec"].startswith("REFER") else "Pending review"

def audit(appid, event):
    t = ts(); st.session_state.audit.append(dict(Time=t, Application=appid, Event=event)); data.save_audit(t, appid, event)

def rec_group(a): return "Approve" if a["rec"].endswith("APPROVE") else "Decline" if a["rec"].endswith("DECLINE") else "Refer"
def agrees(a, c): return (c == "Approved" and rec_group(a) == "Approve") or (c == "Declined" and rec_group(a) == "Decline") or (c == "Info requested" and rec_group(a) == "Refer")

# ---------- Sidebar ----------
st.sidebar.title("Fictional Bank")
st.sidebar.caption("Fictional bank | Proof of concept | Synthetic data only")
page = st.sidebar.radio("Navigate", ["Loan Approval Workbench", "Approach Story", "Technical Architecture", "About and FAQ"])
(st.sidebar.success if DATA_SOURCE.startswith("BigQuery") else st.sidebar.info)(f"Data source: {DATA_SOURCE}")
st.sidebar.caption(f"Credit profile source: {PROFILE_SOURCE}")
st.sidebar.warning("AI output is a recommendation only. It is not a sanction or a legally binding lending decision.")
with st.sidebar.expander("Policy settings (illustrative, not RBI rules)"):
    policy.T["score_fail"] = st.number_input("Decline below bureau score", 300, 900, 680, key="t1")
    policy.T["score_refer"] = st.number_input("Manual review below bureau score", 300, 900, 720, key="t2")
    policy.T["foir_fail"] = st.number_input("Decline above FOIR %", 10, 100, 50, key="t3")
    policy.T["foir_refer"] = st.number_input("Manual review above FOIR %", 10, 100, 40, key="t4")
for a in APPS:
    a.update(run_agents(a, PROFILES.get(a["id"]) if PROFILES else None, PROFILE_SOURCE if PROFILES else None))

# ---------- Page 1 ----------
def workbench():
    st.title("Retail Personal Loan Approval Workbench")
    apps = all_apps()
    sts = [status(a) for a in apps]
    c = st.columns(5)
    c[0].metric("Received", len(apps))
    c[1].metric("Pending review", sts.count("Pending review"))
    c[2].metric("Approved", sts.count("Approved"))
    c[3].metric("Declined", sts.count("Declined"))
    c[4].metric("Flagged", sts.count("Flagged"))

    df = pd.DataFrame([dict(ID=a["id"], Applicant=a["name"], Amount=a["amount"], MonthlyIncome=a["income"], CreditScore=a["score"], DTI_pct=round(a["foir"], 1), Status=status(a), AI=rec_group(a), Scenario=a["scenario"]) for a in apps])
    q = st.text_input("Search register (ID, name, status, scenario)")
    if q:
        df = df[df.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    st.dataframe(df, width="stretch", hide_index=True)
    st.subheader("Portfolio view")
    c1, c2, c3 = st.columns(3)
    c1.plotly_chart(px.bar(df.groupby("AI").size().reset_index(name="Applications"), x="AI", y="Applications", color="AI", title="AI recommendation mix"), width="stretch")
    c2.plotly_chart(px.histogram(df, x="CreditScore", color="AI", nbins=20, title="Bureau score by recommendation"), width="stretch")
    dec = [(x, st.session_state.decisions[x["id"]]) for x in apps if x["id"] in st.session_state.decisions]
    if dec:
        c3.metric("Officer overrides", f"{sum(1 for x, d in dec if not agrees(x, d['decision']))} of {len(dec)}")
        c3.plotly_chart(px.histogram(pd.DataFrame([dict(AI=rec_group(x), Officer=d["decision"]) for x, d in dec]), x="AI", color="Officer", barmode="group", title="Officer decision vs AI"), width="stretch")
    else:
        c3.info("No officer decisions yet. Record one to see override rates.")

    tab_detail, tab_new = st.tabs(["Application detail", "New application"])
    with tab_new:
        with st.form("new"):
            n = st.text_input("Applicant name", "Test Applicant")
            c1, c2, c3 = st.columns(3)
            age = c1.number_input("Age", 18, 80, 30)
            inc = c2.number_input("Monthly income (INR)", 10000, 1000000, 60000, 5000)
            ex = c3.number_input("Existing EMIs (INR)", 0, 500000, 5000, 1000)
            amt = c1.number_input("Requested amount (INR)", 50000, 5000000, 300000, 50000)
            ten = c2.selectbox("Tenure (months)", [12, 24, 36, 48, 60], 2)
            yrs = c3.number_input("Years in employment", 0, 40, 3)
            files = st.file_uploader("Sample PDFs (PAN, salary slip, bank statement)", type="pdf", accept_multiple_files=True)
            if st.form_submit_button("Submit application"):
                docs, dfind = docreader.analyse(files)
                score = 600 + (hash(n) % 200)  # mock bureau, synthetic
                na = dict(id=f"PL-{9001 + len(st.session_state.extra)}", name=n, age=age, income=inc, emi=ex, amount=amt, tenure=ten, score=score, docs=docs or ["PAN"], doc_findings=dfind or None, pan_name=n, years=yrs, scenario="User submitted")
                na.update(run_agents(na))
                st.session_state.extra.append(na)
                audit(na["id"], "Application submitted; agents run")
                st.success(f"Submitted as {na['id']}. Text-based PDFs are read with pypdf; try the files in the samples folder.")
                st.rerun()
    with tab_detail:
        sel = st.selectbox("Select application", [a["id"] for a in apps])
        detail(next(a for a in apps if a["id"] == sel))

def detail(a):
    st.subheader(f"{a['id']} - {a['name']} ({a['scenario']})")
    steps = ["Submitted", "Documents", "Customer & credit", "Affordability & policy", "Risk", "Human decision", "Sanction", "Disbursement"]
    d = st.session_state.decisions.get(a["id"])
    done = 5 + (d is not None) + (d is not None and d["decision"] == "Approved") + (a["id"] in st.session_state.disbursed)
    st.progress(min(done, 8) / 8, text=" -> ".join(f"**{s}**" if i < done else s for i, s in enumerate(steps)))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Risk and affordability**")
        st.write(f"Credit score (mock bureau): **{a['score']}**")
        st.write(f"Proposed EMI: **INR {a['new_emi']:,.0f}** at {RATE}% p.a. for {a['tenure']} months")
        st.write(f"FOIR after loan: **{a['foir']:.1f}%** (cap {policy.T['foir_fail']}%)")
        st.markdown(f"### {a['rec']}")
        st.caption(f"Decision authority (illustrative delegation): {a['authority']}")
        st.caption("Agent output validation: " + ("passed" if a["validated"] else "FAILED, escalated to a human"))
        for f in a["flags"] or ["No risk flags raised"]:
            st.write("- " + f)
    with c2:
        st.markdown("**Data source panel**")
        st.dataframe(pd.DataFrame([
            ("Name, age, income", "Application form (synthetic)"), ("Credit score", "Mock bureau API (simulated)"),
            ("PAN name", "Mock identity verification (simulated)"), ("Existing EMIs", "Synthetic account data (BigQuery in target design)"),
            ("Policy rules", "Synthetic policy PL-2026 v1")], columns=["Field", "Source"]), hide_index=True, width="stretch")
    with st.expander("Existing loans and repayment history (last 12 months)"):
        st.caption("Source: " + a["credit"]["source"])
        if a["profile"]["loans"]:
            st.dataframe(pd.DataFrame(a["profile"]["loans"]).drop(columns=["applicant_id"], errors="ignore"), hide_index=True, width="stretch")
            late = [r for r in a["profile"]["repayments"] if r["days_past_due"] > 0]
            if late:
                st.dataframe(pd.DataFrame(late)[["loan_id", "month", "days_past_due", "status"]], hide_index=True, width="stretch")
            else:
                st.success("No late payments in the last 12 months.")
        else:
            st.info("No existing loan accounts.")
    with st.expander("External checks (all MOCK responses)"):
        st.dataframe(pd.DataFrame([dict(Service=r["service"], Status=r["status"], Detail=r["note"], SimulatedLatencyMs=r["latency_ms"], Label=r["label"]) for r in a["ext"].values()]), hide_index=True, width="stretch")
    with st.expander("Policy evidence: clause-level findings", expanded=True):
        st.caption(policy.POLICY_NAME)
        st.dataframe(pd.DataFrame([dict(Check=f["check"], Result=f["result"], Why=f["detail"], Evidence=f["evidence"], Clause=f["clause_id"],
                                        ClauseText=f["clause_text"], Source=f["source"]) for f in a["findings"]]), hide_index=True, width="stretch")
    st.markdown("**Agent activity log**")
    st.dataframe(pd.DataFrame(a["log"]), hide_index=True, width="stretch")

    st.markdown("**Human credit officer review**")
    if d:
        st.info(f"Decision: {d['decision']} by {d['officer']} at {d['time']}. Reason: {d['reason'] or 'Agrees with recommendation'}")
    else:
        officer = st.text_input("Officer name", "Credit Officer 1", key="of" + a["id"])
        choice = st.radio("Decision", ["Approved", "Declined", "Info requested"], horizontal=True, key="ch" + a["id"])
        reason = st.text_area("Override reason (required if you differ from the AI recommendation)", key="rs" + a["id"])
        agrees = (choice == "Approved" and a["rec"].endswith("APPROVE")) or (choice == "Declined" and a["rec"].endswith("DECLINE")) or (choice == "Info requested" and a["rec"].startswith("REFER"))
        if st.button("Record decision", key="bt" + a["id"]):
            if not agrees and not reason.strip():
                st.error("An override reason is required when disagreeing with the recommendation.")
            else:
                st.session_state.decisions[a["id"]] = dict(decision=choice, reason=reason, officer=officer, time=ts()); data.save_decision(a["id"], st.session_state.decisions[a["id"]])
                audit(a["id"], f"{officer} recorded '{choice}' ({'agrees with' if agrees else 'OVERRIDES'} AI: {a['rec']})")
                st.rerun()
    if d and d["decision"] == "Approved":
        st.markdown("**Sanction terms (simulated)**")
        tot = a["new_emi"] * a["tenure"]
        st.dataframe(pd.DataFrame([("Sanctioned amount", f"INR {a['amount']:,}"), ("Interest rate (illustrative)", f"{RATE}% p.a."), ("Tenure", f"{a['tenure']} months"),
            ("EMI", f"INR {a['new_emi']:,.0f}"), ("Processing fee (1%)", f"INR {a['amount'] * 0.01:,.0f}"), ("Total interest", f"INR {tot - a['amount']:,.0f}"),
            ("Total payable", f"INR {tot:,.0f}"), ("Cooling-off", "3 days to exit without penalty (fictional bank policy)")], columns=["Item", "Value"]), hide_index=True, width="stretch")
        st.caption("Illustrative Key Fact Statement style summary. Not a regulatory document.")
        if a["id"] not in st.session_state.accepted:
            st.caption("Stage 2 of 3: customer acceptance of sanction terms")
            if st.button("Record customer acceptance of terms (simulated)", key="ac" + a["id"]):
                st.session_state.accepted.add(a["id"]); data.save_stage(a["id"], "accepted"); audit(a["id"], "Sanction terms accepted (simulated)"); st.rerun()
        elif a["id"] in st.session_state.disbursed:
            st.success("Simulated disbursement completed. No real funds were moved.")
        else:
            st.caption("Stage 3 of 3: disbursement")
            if st.button("Simulate disbursement", key="db" + a["id"]):
                st.session_state.disbursed.add(a["id"]); data.save_stage(a["id"], "disbursed"); audit(a["id"], "Simulated disbursement"); st.rerun()
    st.markdown("**Audit trail**")
    tr = [r for r in st.session_state.audit if r["Application"] == a["id"]]
    st.dataframe(pd.DataFrame(tr) if tr else pd.DataFrame(columns=["Time", "Application", "Event"]), hide_index=True, width="stretch")

# ---------- Page 2 ----------
def card(title, body, accent="#1f4e8c"):
    return (f'<div style="border-left:5px solid {accent};background:rgba(120,140,170,.12);padding:12px 14px;'
            f'border-radius:6px;height:100%"><div style="font-weight:700;margin-bottom:4px">{title}</div>'
            f'<div style="font-size:.92rem;line-height:1.4">{body}</div></div>')

def cards(items, accent):
    cols = st.columns(len(items))
    for c, (t, b) in zip(cols, items):
        c.markdown(card(t, b, accent), unsafe_allow_html=True)

def story():
    st.title("Approach Story")
    st.caption("Written for the Retail Lending Head. Fictional bank, synthetic data, proof of concept.")
    st.markdown("""
\n**1. Lending decisions depend on three kinds of information that live in different places.** Policies and documents, core banking records, and outside checks.
\n**2. Act 1 brings them into one trusted data foundation** so every check starts from the same facts.
\n**3. Act 2 puts specialist AI agents on top** to check documents, apply policy, tests affordability and assemble evidence. **A credit officer still makes every decision.**""")
    st.divider()

    st.header("Act 1: The Lakehouse")
    st.write("Today an officer gathers these by hand. The lakehouse gathers them once, checks quality, and keeps them together.")
    cards([("Unstructured", "Credit policies, RBI circulars, identity documents, salary slips, bank statements, income-tax documents"),
           ("Structured", "Customer profiles, account transactions, existing loans, repayment history"),
           ("External (mock in this demo)", "Credit bureau score, identity verification, collateral or charge checks where relevant, GST or account aggregator data where applicable")], "#1f4e8c")
    st.write("")
    st.graphviz_chart("""digraph{rankdir=LR;nodesep=.3;node[shape=box,style="rounded,filled",fontname="Helvetica",fillcolor="#e8effa",color="#1f4e8c"];
A[label="1 Ingest\\nbring data in"];B[label="2 Validate\\ncomplete? readable?"];C[label="3 Standardise\\none format, one meaning"];D[label="4 Quality checks\\nflag gaps and conflicts"];
L[label="BigQuery lending\\ndata foundation",fillcolor="#1f4e8c",fontcolor="white"];A->B->C->D->L}""")
    st.info("In this demo the foundation is simulated with local synthetic data. The target design uses BigQuery.")
    st.divider()

    st.header("Act 2: Agentic AI on top of the foundation")
    st.write("Each agent has one job, shows its evidence, and hands over to the next. Anything doubtful goes to a person.")
    st.graphviz_chart("""digraph{rankdir=LR;nodesep=.35;node[shape=box,style="rounded,filled",fontname="Helvetica",fillcolor="#e9f5ea",color="#2e7d32"];
D[label="Document\\nagent"];P[label="Policy\\nagent"];C[label="Credit and\\naffordability agent"];R[label="Recommendation\\nagent"];
H[label="Credit officer\\ndecides",fillcolor="#ffe9c7",color="#c77700",shape=box];
D->P->C->R->H;D->H[style=dashed,label=" conflict"];C->H[style=dashed,label=" high risk"]}""")
    cards([("Document agent", "Finds missing or conflicting information, such as a name that differs across records."),
           ("Policy agent", "Retrieves the relevant lending rule and applies it, citing the reference."),
           ("Credit and affordability agent", "Reads bureau data, computes the EMI and the share of income already committed."),
           ("Recommendation agent", "Assembles one evidence-based summary: approve for consideration, review, or decline.")], "#2e7d32")
    st.write("")
    st.subheader("Where people stay in control")
    cards([("Always human", "The approve, decline or request-information decision, and any override with a written reason."),
           ("Escalated automatically", "Missing documents, conflicting evidence, policy exceptions, high-risk flags."),
           ("Never claimed", "An AI recommendation is not a sanction and is not a legally binding decision.")], "#c77700")
    st.divider()

    st.header("Potential business value")
    st.caption("These are expected benefits to test in a pilot. This demo has no measured results.")
    st.table(pd.DataFrame({
        "Benefit": ["Less manual effort", "More consistent checks", "Better traceability", "Potentially shorter turnaround"],
        "How it could happen": ["Routine document and rule checks are prepared automatically", "The same rules and thresholds apply to every file", "Every step records the agent, evidence, outcome and time", "Fewer hand-offs and less re-keying"],
        "How a pilot would measure it": ["Officer minutes per file", "Variation in outcomes on similar files", "Share of decisions with a complete evidence trail", "Days from application to decision"]}))
    st.divider()
    st.subheader("What this demo is, and is not")
    c1, c2 = st.columns(2)
    c1.success("**Is:** a working walkthrough of the journey, agent hand-offs, evidence and human decision, on synthetic data.")
    c2.warning("**Is not:** a production system, a live bureau or KYC integration, or proof of measured improvement.")

# ---------- Page 3 ----------
def arch():
    st.title("Architecture")
    st.caption("Business view first, then the technical view. Status labels reflect what exists in this code today.")
    tab_b, tab_t = st.tabs(["Business architecture", "Technical architecture"])
    with tab_b:
        st.subheader("Business layers and the loan journey")
        st.graphviz_chart("""digraph{rankdir=TB;compound=true;nodesep=.25;ranksep=.35;node[shape=box,style="rounded,filled",fontname="Helvetica",fillcolor="#eef3fb",color="#1f4e8c"];
subgraph cluster1{label="1  Engagement";style=rounded;color="#1f4e8c";E[label="Applicant intake and\\ncredit officer workbench"]}
subgraph cluster2{label="2  Process orchestration";style=rounded;color="#1f4e8c";
P[label="Application > Documents > Credit checks > Affordability and policy > Risk > Human decision > Sanction > Disbursement",fillcolor="#e8effa"]}
subgraph cluster3{label="3  Decision intelligence (agents)";style=rounded;color="#2e7d32";
A1[label="Document\\nagent",fillcolor="#e9f5ea",color="#2e7d32"];A2[label="Policy\\nagent",fillcolor="#e9f5ea",color="#2e7d32"];A3[label="Credit and\\naffordability",fillcolor="#e9f5ea",color="#2e7d32"];A4[label="Recommendation\\nagent",fillcolor="#e9f5ea",color="#2e7d32"]}
subgraph cluster4{label="4  Business rules and knowledge";style=rounded;color="#6a1b9a";K1[label="Lending policy clauses",fillcolor="#f3e8f8",color="#6a1b9a"];K2[label="Affordability formulas\\nand thresholds",fillcolor="#f3e8f8",color="#6a1b9a"]}
subgraph cluster5{label="5  Data foundation (lakehouse)";style=rounded;color="#455a64";D1[label="Unstructured\\npolicies, documents",fillcolor="#eceff1",color="#455a64"];D2[label="Structured\\ncustomer and loan data",fillcolor="#eceff1",color="#455a64"];D3[label="External (mock)\\nbureau, identity, fraud",fillcolor="#eceff1",color="#455a64"]}
subgraph cluster6{label="6  Control and governance";style=rounded;color="#c77700";G1[label="Human credit officer\\nfinal decision",fillcolor="#ffe9c7",color="#c77700"];G2[label="Audit trail and\\nexplainability",fillcolor="#ffe9c7",color="#c77700"];G3[label="Access control and\\ndata protection",fillcolor="#ffe9c7",color="#c77700"]}
E->P;P->A1;P->A3;A1->A2->A4;A3->A4;A2->K1;A3->K2;A1->D1;A3->D2;A3->D3;A4->G1;G1->G2[style=dashed];G1->G3[style=dashed]}""")
        st.subheader("Who does what at each stage")
        st.dataframe(pd.DataFrame([
            ("1 Application", "Applicant or relationship manager", "Form details", "Mandatory fields captured"),
            ("2 Document verification", "Document agent", "PAN, salary slip, statement", "Missing or conflicting items escalated"),
            ("3 Customer and credit checks", "Credit agent (mock bureau)", "Bureau score, existing EMIs", "Adverse indicators flagged"),
            ("4 Affordability and policy", "Policy and credit agents", "Income, EMI, policy clauses", "Each result cites a clause"),
            ("5 Risk assessment", "Recommendation agent", "All findings", "Exceptions escalated to a person"),
            ("6 Credit decision", "Credit officer", "Evidence pack", "Override reason mandatory"),
            ("7 Sanction and acceptance", "Credit officer, customer (simulated)", "Sanction terms", "Separate stages"),
            ("8 Disbursement", "Operations (simulated)", "Accepted terms", "Only after acceptance")],
            columns=["Stage", "Who acts", "Data used", "Control point"]), hide_index=True, width="stretch")
        st.caption("Not modelled: a real Key Fact Statement and cooling-off process (an illustrative summary is shown) and a real fraud service.")
    with tab_t:
        st.subheader("Technical components")
        st.graphviz_chart("""digraph{rankdir=TB;node[shape=box,style="rounded,filled",fontname="Helvetica",fillcolor="#eef3fb"];
SRC[label="1 Data sources\\n(documents, core banking, mock external)"];ING[label="2 Ingestion and extraction"];VAL[label="3 Validation and transformation (Pandas)"];
BQ[label="4 BigQuery (target) / SQLite-local fallback",fillcolor="#d6e6ff"];RET[label="5 Policy clause retrieval"];
AG[label="6 AI agents and tools",fillcolor="#eef7ee"];EXT[label="7 Mock external APIs",fillcolor="#f3f3f3"];BR[label="8 Business rules and affordability"];
UI[label="9 Streamlit UI"];HUM[label="10 Human credit officer",fillcolor="#ffe9c7"];GOV[label="11 Audit, access control, governance",fillcolor="#fde2e2"];
SRC->ING->VAL->BQ->RET->AG;EXT->AG;BR->AG;AG->UI->HUM;HUM->GOV;AG->GOV[style=dashed]}""")
        st.table(pd.DataFrame([
            ("Intake and workbench", "Streamlit app (app.py)", "Implemented"),
            ("Document review", "Document agent + docreader.py (pypdf)", "Implemented for text PDFs you upload (name, income); pre-generated findings for built-in cases; no OCR"),
            ("Bureau, PAN, bank and fraud checks", "mocks.py (local mock services)", "Simulated: deterministic mock responses incl. unavailable, inconsistent and adverse cases"),
            ("Delegation of authority", "policy.authority()", "Implemented as fictional amount bands; display only"),
            ("Affordability", "logic.py (EMI, FOIR)", "Implemented, unit tested"),
            ("Policy lookup and rules", "policy.py reading policy_docs/*.txt (11 illustrative clauses, keyword retrieval, Python rules)", "Implemented, unit tested; thresholds editable in sidebar"),
            ("Recommendation", "Rule-based, no LLM", "Implemented"),
            ("Human decision and stages", "Streamlit controls; override reason required", "Implemented; sanction, acceptance and disbursement are simulated"),
            ("Audit trail", "SQLite, with best-effort copy to BigQuery", "Implemented; BigQuery copy not guaranteed"),
            ("Credit and repayment review", "agents.py credit_assess over existing_loans and repayment_history", "Implemented on synthetic data; read from BigQuery when those tables are loaded"),
            ("Agent output validation", "agents.py validate_output", "Implemented: structure checks; invalid output is escalated to a human"),
            ("Data platform", "BigQuery: 12 tables via load_to_bigquery.py; local fallback; CSV export via generate_data.py", "Implemented; decisions and audit events are copied best-effort; never tested against your production data by me"),
            ("Access control and encryption", "Cloud IAM, role-based access", "Conceptual, not implemented"),
            ("LLM summaries", "None", "Not built")], columns=["Business function", "Technical component", "Status"]))

def about():
    st.title("About and FAQ")
    st.markdown("""**Purpose:** show presales stakeholders how agentic AI could support retail personal loan assessment, with a person making every final decision.
**Intended users:** retail lending heads, credit officers, presales evaluators.
**Scope and assumptions:** fictional bank, one product (personal loan), illustrative policy settings (min score 680, FOIR cap 50%, age 21-60). These are not RBI rules.
**Synthetic data:** all applicants, scores and documents are fictional. Mock services only; no real systems are called.""")
    for q, ans in [("Does the AI approve loans?", "No. It produces a recommendation with evidence. A credit officer decides and must justify any override."),
                   ("Is an LLM used?", "No. Agents here are deterministic Python rules. An LLM could be added later as an optional, off-by-default summariser, never the sole decision-maker."),
                   ("Is BigQuery used?", "Optionally. The sidebar says whether data really came from BigQuery or from local synthetic data.")]:
        with st.expander(q): st.write(ans)
    st.subheader("Limitations and future work")
    st.markdown("- Agents are deterministic rules, not an LLM\n- PDF reading works for text PDFs only; no OCR\n- Bureau, PAN, bank and fraud services are local mocks\n- BigQuery holds 12 synthetic tables; decisions and audit events are copied best-effort\n- No real Key Fact Statement or cooling-off process")
    st.subheader("Contact")
    st.write("Presales team: presales@fictional.com | +91-00000-00000")
    st.caption("Placeholder contact details for this demo.")

{"Loan Approval Workbench": workbench, "About and FAQ": about, "Approach Story": story, "Technical Architecture": arch}[page]()