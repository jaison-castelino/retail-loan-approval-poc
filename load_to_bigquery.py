"""One-off: create tables in your BigQuery dataset and upload the synthetic applicants.
Run:  python load_to_bigquery.py"""
import bq, data
ok, msg = bq.ping()
print("Connection:", msg)
if ok:
    apps = data.DEMO_APPS + data.generate_applicants(294)
    bq.setup_and_load(apps)
    print(f"Uploaded {len(apps)} applicants to {bq.PROJECT}.{bq.DATASET}.applicants")
