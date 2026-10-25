"""Synthetic applicant generator + SQLite persistence (local fallback; BigQuery not implemented)."""
import os, random, sqlite3
FIRST = ["Aarav","Diya","Vihaan","Isha","Arjun","Neha","Karthik","Pooja","Sanjay","Lakshmi","Farhan","Riya","Manoj","Sneha","Harish","Divya"]
LAST = ["Shetty","Kulkarni","Menon","Gupta","Pillai","Reddy","Bhat","Joshi","Khan","Patel","Naik","Das","Rao","Iyer","Singh","Hegde"]
DEMO_APPS = [
    dict(id="PL-1001", name="Ananya Rao", age=32, income=95000, emi=8000, amount=500000, tenure=48, score=781, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Ananya Rao", years=6, scenario="Clean approval"),
    dict(id="PL-1002", name="Rohit Verma", age=41, income=70000, emi=6000, amount=400000, tenure=36, score=742, docs=["PAN", "Salary slip"], pan_name="Rohit Verma", years=9, scenario="Incomplete documents"),
    dict(id="PL-1003", name="Sunil Das", age=29, income=38000, emi=17000, amount=600000, tenure=36, score=612, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Sunil Das", years=2, scenario="High risk"),
    dict(id="PL-1004", name="Meera Nair", age=37, income=60000, emi=14000, amount=450000, tenure=48, score=702, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Meera Nair", years=4, scenario="Borderline - manual review"),
    dict(id="PL-1005", name="Imran Sheikh", age=35, income=82000, emi=5000, amount=350000, tenure=36, score=755, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Imran Shaikh", years=7, scenario="Name conflict across documents"),
    dict(id="PL-1006", name="Kavya Iyer", age=26, income=55000, emi=0, amount=250000, tenure=24, score=728, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Kavya Iyer", years=3, scenario="Clean approval"),
    dict(id="PL-1007", name="Nikhil Bhat", age=34, income=88000, emi=6000, amount=400000, tenure=36, score=748, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Nikhil Bhat", years=8, scenario="Fraud screening flag"),
    dict(id="PL-1008", name="Sara Thomas", age=30, income=72000, emi=3000, amount=300000, tenure=36, score=735, docs=["PAN", "Salary slip", "Bank statement"], pan_name="Sara Thomas", years=5, scenario="Bureau service unavailable"),
]

def default_applicants(n=300):
    """8 fixed demo cases plus generated applicants, n in total (repeatable)."""
    if n < len(DEMO_APPS): raise ValueError(f"n must be at least {len(DEMO_APPS)}")
    return DEMO_APPS + generate_applicants(n - len(DEMO_APPS))

DOCS = ["PAN", "Salary slip", "Bank statement"]

def generate_applicants(n=294, seed=7, start=2001):
    rnd = random.Random(seed); out = []
    for i in range(n):
        name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        income = int(rnd.uniform(25000, 200000) // 1000 * 1000)
        docs = list(DOCS); scen = "Generated"
        if rnd.random() < 0.08: docs.remove(rnd.choice(DOCS)); scen = "Generated - incomplete documents"
        pan = name
        if rnd.random() < 0.05: pan = name.replace("a", "e", 1); scen = "Generated - name conflict"
        out.append(dict(id=f"PL-{start + i}", name=name, age=rnd.randint(21, 58), income=income,
            emi=int(income * rnd.uniform(0, 0.4) // 500 * 500), amount=rnd.randint(2, 30) * 50000,
            tenure=rnd.choice([12, 24, 36, 48, 60]), score=int(min(830, max(560, rnd.gauss(705, 60)))),
            docs=docs, pan_name=pan, years=rnd.randint(0, 20), scenario=scen))
    return out

def load_applicants():
    """Return (applicants, source label). Uses BigQuery only if it is reachable AND holds data; else local synthetic data."""
    import bq
    if bq.configured():
        ok, msg = bq.ping()
        if ok:
            try:
                rows = bq.read_applicants()
                if rows: return rows, f"BigQuery ({bq.PROJECT}.{bq.DATASET}), {len(rows)} applicants"
                msg = "dataset connected but applicants table is empty (run load_to_bigquery.py)"
            except Exception as e: msg = str(e)[:150]
        return default_applicants(), f"LOCAL synthetic data (BigQuery not used: {msg})"
    return default_applicants(), "LOCAL synthetic data (BigQuery not configured)"

def load_profiles(apps):
    """Return (profiles by applicant id or None, source label). Reads BigQuery tables only if they exist and hold data."""
    import bq
    if bq.configured() and bq.ping()[0]:
        try:
            loans, reps = bq.read_table("existing_loans"), bq.read_table("repayment_history")
            if loans or reps:
                idx = {a["id"]: dict(loans=[], repayments=[]) for a in apps}
                for r in loans:
                    if r["applicant_id"] in idx: idx[r["applicant_id"]]["loans"].append(r)
                for r in reps:
                    if r["applicant_id"] in idx: idx[r["applicant_id"]]["repayments"].append(r)
                return idx, "BigQuery tables existing_loans and repayment_history"
        except Exception:
            pass
    return None, "Synthetic (local generator)"

def _db():
    c = sqlite3.connect(os.environ.get("LOAN_DB", "loan_demo.db"))
    c.executescript("""CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY, decision TEXT, reason TEXT, officer TEXT, time TEXT);
    CREATE TABLE IF NOT EXISTS audit(time TEXT, application TEXT, event TEXT);
    CREATE TABLE IF NOT EXISTS stages(id TEXT, stage TEXT, PRIMARY KEY(id, stage));""")
    return c

def load_state():
    c = _db()
    dec = {r[0]: dict(decision=r[1], reason=r[2], officer=r[3], time=r[4]) for r in c.execute("SELECT * FROM decisions")}
    aud = [dict(Time=r[0], Application=r[1], Event=r[2]) for r in c.execute("SELECT * FROM audit ORDER BY rowid")]
    st = c.execute("SELECT id, stage FROM stages").fetchall(); c.close()
    return dec, aud, {i for i, s in st if s == "accepted"}, {i for i, s in st if s == "disbursed"}

def save_decision(i, d):
    c = _db(); c.execute("INSERT OR REPLACE INTO decisions VALUES(?,?,?,?,?)", (i, d["decision"], d["reason"], d["officer"], d["time"])); c.commit(); c.close()
    import bq; bq.mirror('decisions', dict(id=i, **d))

def save_audit(t, app, ev):
    c = _db(); c.execute("INSERT INTO audit VALUES(?,?,?)", (t, app, ev)); c.commit(); c.close()
    import bq; bq.mirror("audit_events", dict(time=t, application=app, event=ev))

def save_stage(i, stage):
    c = _db(); c.execute("INSERT OR IGNORE INTO stages VALUES(?,?)", (i, stage)); c.commit(); c.close()
