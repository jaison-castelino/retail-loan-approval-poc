"""Create the BigQuery tables and upload synthetic data.
Usage:  python load_to_bigquery.py --n 1000
Replaces the generated tables. Never touches existing rows in decisions or audit_events."""
import argparse
import bq, data, tables

p = argparse.ArgumentParser(); p.add_argument("--n", type=int, default=300); args = p.parse_args()
ok, msg = bq.ping(); print("Connection:", msg)
if ok:
    tbl = tables.build_tables(data.default_applicants(args.n))
    bq.load_all(tbl)
    for n, rows in tbl.items(): print(f"{n}: {len(rows)} rows" if n not in ("decisions", "audit_events") else f"{n}: created if missing, existing rows kept")
    print(f"Uploaded to {bq.PROJECT}.{bq.DATASET}")
