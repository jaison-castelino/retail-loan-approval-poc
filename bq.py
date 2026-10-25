"""Optional BigQuery layer. Credentials come from gcloud login (ADC); names from .env. Nothing is hard-coded."""
import os

def _load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
_load_env()
PROJECT, DATASET = os.environ.get("GCP_PROJECT_ID", ""), os.environ.get("BQ_DATASET", "")
last_error = ""

def configured():
    return bool(PROJECT and DATASET)

def _client():
    """Use a service-account key from secrets if provided (hosted apps); otherwise fall back to gcloud login (local)."""
    from google.cloud import bigquery
    info = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if not info:
        try:
            import streamlit as st
            if "gcp_service_account" in st.secrets: info = dict(st.secrets["gcp_service_account"])
        except Exception:
            pass
    if info:
        import json
        from google.oauth2 import service_account
        info = json.loads(info) if isinstance(info, str) else info
        return bigquery.Client(project=PROJECT, credentials=service_account.Credentials.from_service_account_info(info))
    return bigquery.Client(project=PROJECT)

SPEC = {
    "applicants": "id:S name:S age:I income:I emi:I amount:I tenure:I score:I docs:S* pan_name:S years:I scenario:S",
    "decisions": "id:S decision:S reason:S officer:S time:S",
    "audit_events": "time:S application:S event:S",
    "loan_applications": "application_id:S applicant_id:S requested_amount:I tenure_months:I purpose:S submitted_on:S recommendation:S",
    "customer_accounts": "account_id:S applicant_id:S account_type:S avg_balance:I years_open:I",
    "transactions": "txn_id:S applicant_id:S account_id:S month:S txn_type:S amount:I",
    "existing_loans": "loan_id:S applicant_id:S loan_type:S monthly_emi:I outstanding:I remaining_months:I",
    "repayment_history": "loan_id:S applicant_id:S month:S days_past_due:I status:S",
    "bureau_results": "applicant_id:S status:S score:I enquiries_6m:I active_loans:I note:S latency_ms:I",
    "document_findings": "applicant_id:S doc_type:S status:S source:S",
    "policy_rules": "clause_id:S title:S text:S",
    "agent_logs": "application_id:S seq:I agent:S action:S evidence:S outcome:S source:S timestamp:S"}

def _schemas():
    from google.cloud.bigquery import SchemaField as F
    types = {"S": "STRING", "I": "INTEGER"}
    out = {}
    for t, spec in SPEC.items():
        out[t] = [F(f.split(":")[0], types[f.split(":")[1].rstrip("*")], mode="REPEATED" if f.endswith("*") else "NULLABLE") for f in spec.split()]
    return out

def ping():
    """Return (ok, message). Never raises."""
    global last_error
    if not configured(): return False, "GCP_PROJECT_ID / BQ_DATASET not set"
    try:
        _client().get_dataset(f"{PROJECT}.{DATASET}"); return True, "connected"
    except Exception as e:
        last_error = str(e)[:300]; return False, last_error

def _load(table, rows, truncate=False):
    from google.cloud import bigquery
    cfg = bigquery.LoadJobConfig(schema=_schemas()[table], write_disposition="WRITE_TRUNCATE" if truncate else "WRITE_APPEND")
    _client().load_table_from_json(rows, f"{PROJECT}.{DATASET}.{table}", job_config=cfg).result()

def load_all(tables):
    """Create every table, then replace the generated ones. decisions and audit_events are created if missing and never wiped."""
    from google.cloud import bigquery
    c = _client()
    for t, sch in _schemas().items():
        c.create_table(bigquery.Table(f"{PROJECT}.{DATASET}.{t}", schema=sch), exists_ok=True)
    for t, rows in tables.items():
        if t not in ("decisions", "audit_events") and rows: _load(t, rows, truncate=True)

def read_table(name):
    rows = _client().query(f"SELECT * FROM `{PROJECT}.{DATASET}.{name}`").result()
    return [dict(r.items()) for r in rows]

def read_applicants():
    rows = _client().query(f"SELECT * FROM `{PROJECT}.{DATASET}.applicants` ORDER BY id").result()
    return [dict(r.items()) for r in rows]

def mirror(table, row):
    """Best-effort copy of a decision/audit row to BigQuery. Failure is recorded, never fatal."""
    global last_error
    if not configured() or os.environ.get("BQ_MIRROR", "true").lower() == "false": return
    try: _load(table, [row])
    except Exception as e: last_error = str(e)[:300]
