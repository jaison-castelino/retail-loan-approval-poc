"""Standalone synthetic data generator. Writes one CSV per table. Fixed seed, so output is repeatable.
Usage:  python generate_data.py --n 1000 --out generated_data"""
import argparse, csv, os
import data, tables

p = argparse.ArgumentParser()
p.add_argument("--n", type=int, default=300, help="total applicants (8 fixed demo cases + generated; minimum 8)")
p.add_argument("--out", default="generated_data", help="output folder")
args = p.parse_args()
apps = data.default_applicants(args.n)
tbl = tables.build_tables(apps)
os.makedirs(args.out, exist_ok=True)
for name, rows in tbl.items():
    with open(os.path.join(args.out, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        if not rows:
            f.write("");
            continue
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()));
        w.writeheader()
        for r in rows: w.writerow({k: "|".join(v) if isinstance(v, list) else v for k, v in r.items()})
    print(f"{name}: {len(rows)} rows")
print(f"Wrote {len(tbl)} CSV files to {args.out}/  ({len(apps)} synthetic applicants, all fictional)")
