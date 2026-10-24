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
    from google.cloud import bigquery
    return bigquery.Client(project=PROJECT)

def _schemas():
    from google.cloud.bigquery import SchemaField as F
    return {
        "applicants": [F("id", "STRING"), F("name", "STRING"), F("age", "INTEGER"), F("income", "INTEGER"), F("emi", "INTEGER"),
                       F("amount", "INTEGER"), F("tenure", "INTEGER"), F("score", "INTEGER"), F("docs", "STRING", mode="REPEATED"),
                       F("pan_name", "STRING"), F("years", "INTEGER"), F("scenario", "STRING")],
        "decisions": [F("id", "STRING"), F("decision", "STRING"), F("reason", "STRING"), F("officer", "STRING"), F("time", "STRING")],
        "audit_events": [F("time", "STRING"), F("application", "STRING"), F("event", "STRING")]}

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

def setup_and_load(apps):
    """Create tables (via load jobs) and upload applicants. Empty decision/audit tables are created too."""
    from google.cloud import bigquery
    c = _client()
    for t, sch in _schemas().items():
        c.create_table(bigquery.Table(f"{PROJECT}.{DATASET}.{t}", schema=sch), exists_ok=True)
    _load("applicants", [{k: a[k] for k in ("id","name","age","income","emi","amount","tenure","score","docs","pan_name","years","scenario")} for a in apps], truncate=True)

def read_applicants():
    rows = _client().query(f"SELECT * FROM `{PROJECT}.{DATASET}.applicants` ORDER BY id").result()
    return [dict(r.items()) for r in rows]

def mirror(table, row):
    """Best-effort copy of a decision/audit row to BigQuery. Failure is recorded, never fatal."""
    global last_error
    if not configured() or os.environ.get("BQ_MIRROR", "true").lower() == "false": return
    try: _load(table, [row])
    except Exception as e: last_error = str(e)[:300]
