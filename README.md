# Fictional Bank: Agentic AI Personal Loan Approval Workbench

> **Proof of concept using synthetic data only.** The bank is fictional. Nothing here is a real lending decision, and an AI recommendation is **not** a sanction or a legally binding decision. No real bureau, KYC, Aadhaar, PAN or RBI system is called.

A Streamlit demo of how agentic AI could support retail personal loan approval at a mid-sized Indian bank, while keeping a human credit officer in control. It was built for a Business Analyst (Data and AI Presales) assignment.

## Live demo
**https://retail-loan-approval-poc-jaison.streamlit.app/**

Hosted on Streamlit Community Cloud. If the app has been idle it may take a moment to wake up. The sidebar states whether the hosted version is using BigQuery or local synthetic data. To run it yourself, see Quick start below.

## What it demonstrates
The full journey: **application, document verification, credit checks, affordability and policy assessment, risk assessment, human credit decision, sanction, customer acceptance, simulated disbursement.**

- Specialist agents that each show their action, evidence, outcome and timestamp
- Clause-level policy evidence for every check
- Mandatory override reason when the officer disagrees with the recommendation
- A persistent audit trail
- An optional BigQuery data layer with an automatic local fallback

## Quick start
Requires Python 3.10 or newer.

```
pip install -r requirements.txt
streamlit run app.py
```
The app works with no cloud account. The sidebar states the data source honestly: it reads **LOCAL synthetic data** unless BigQuery is really connected.

## Pages
| Page | Purpose |
|---|---|
| Loan Approval Workbench | Metrics, searchable register of 300 applicants, new application form, application detail, agent log, policy evidence, officer decision, sanction and disbursement |
| Approach Story | Two-act explanation for a non-technical lending head: the lakehouse, then agentic AI |
| Architecture | Business architecture (layers and stage-by-stage roles) and technical architecture with an honest implemented versus simulated table |
| About and FAQ | Purpose, scope, role of AI, limitations, placeholder contact details |

## Demo scenarios (deterministic)
| ID | Scenario | Expected recommendation |
|---|---|---|
| PL-1001 | Clean case | Approve for consideration |
| PL-1002 | Bank statement missing | Refer: request documents |
| PL-1003 | Low score, high obligations | Decline recommendation |
| PL-1004 | Borderline score and obligations | Refer: manual review |
| PL-1005 | Name differs from PAN record | Refer: manual review |
| PL-1006 | Clean case, no existing EMIs | Approve for consideration |
| PL-1007 | Mock fraud screening flags the applicant | Refer: manual review |
| PL-1008 | Mock credit bureau unavailable | Refer: manual review |

The other 292 applicants are generated with a fixed random seed, so results are repeatable.

## How decisions are made
- **Document agent:** checks mandatory documents and name consistency against a mock PAN record. For PDFs you upload, it reads the text with pypdf and compares the name and net monthly salary with the application. Built-in cases use pre-generated findings, labelled as simulated. Try the files in `samples/`.
- **Mock services (`mocks.py`):** bureau, PAN, bank account and fraud responses, all labelled MOCK, including unavailable, inconsistent and adverse cases.
- **Credit and affordability agent:** reads a mock bureau score and computes the proposed EMI with the standard amortisation formula. Fixed obligations to income (FOIR) is defined as `(existing EMIs + proposed EMI) / gross monthly income`.
- **Policy agent:** retrieves the matching clause from 8 illustrative policy clauses by keyword overlap (no vector database) and applies plain Python rules, citing the clause for every result.
- **Recommendation agent:** combines the findings into one of: approve for consideration, refer, or decline recommendation.
- **Credit officer:** records Approve, Decline or Request information. Disagreeing with the recommendation requires a written reason. Approval leads to three separate steps: sanction terms, customer acceptance, disbursement.

No LLM is used, and no API key is required. Thresholds (illustrative bank settings, **not RBI rules**) are in `policy.py`: age 21 to 60, 2 years employment, score decline below 680 and review below 720, FOIR decline above 50% and review above 40%, loan up to 12 times monthly income.

## Optional: BigQuery
1. Create a Google Cloud project and a BigQuery dataset.
2. Run `gcloud auth application-default login` (the command must contain `application-default`).
3. Copy `.env.example` to `.env` and set `GCP_PROJECT_ID` and `BQ_DATASET`. Never commit `.env`.
4. Run `python load_to_bigquery.py` (add `--n 1000` for 1,000 applicants). It creates 12 tables and uploads the synthetic data.
5. After pulling a new version, re-run the load script so BigQuery has the newest demo applicants (it replaces the applicants table). Restart the app. The sidebar turns green only when BigQuery is actually used.

Tables (12): `applicants`, `loan_applications`, `customer_accounts`, `transactions`, `existing_loans`, `repayment_history`, `bureau_results`, `document_findings`, `policy_rules`, `agent_logs`, `decisions`, `audit_events`. The loader replaces the generated tables on every run but never wipes `decisions` or `audit_events`. Decisions and audit events are saved to local SQLite first and copied to BigQuery on a best-effort basis (`BQ_MIRROR=false` turns the copy off). The credit agent reads `existing_loans` and `repayment_history` from BigQuery when they are loaded, otherwise it uses the local generator, and the sidebar says which.
The free BigQuery sandbox may block writes and expires tables after 60 days. Enabling billing stays free within the free-tier limits.

## Project structure
```
app.py                  Streamlit UI, four pages, agent orchestration
agents.py               Agent orchestration (document, credit, risk, affordability, policy, recommendation) and output validation
policy.py               Policy agent: retrieval over policy_docs/, rules, approval authority
synth.py                Synthetic accounts, transactions, existing loans and repayment history
tables.py               Builds all 12 tables for CSV export and BigQuery
generate_data.py        Standalone generator: writes one CSV per table (python generate_data.py --n 1000)
policy_docs/            12 illustrative policy clauses as text files
mocks.py                Local mock bureau, PAN, bank and fraud services
docreader.py            PDF text extraction with pypdf
make_sample_pdfs.py     Creates synthetic sample PDFs in samples/ (needs reportlab)
samples/                Sample salary slip, statement and PAN PDFs
logic.py                EMI and FOIR calculations
data.py                 Synthetic data generator, SQLite persistence, data source selection
bq.py                   Optional BigQuery layer
load_to_bigquery.py     One-off table creation and upload
tests/                  Unit tests
docs/                   Documentation required during submission
requirements.txt        Dependencies
.env.example            Configuration template (no secrets)
```

## Generate data without BigQuery
```
python generate_data.py --n 1000 --out generated_data
```
Writes 12 CSV files with a fixed seed, so the data is repeatable. All data is fictional.

## Tests
```
pip install pytest
pytest
```

## What is implemented, simulated and not built
**Implemented:** credit review of existing loans and 12-month repayment history, validation of agent outputs (invalid output is escalated to a human), a standalone data generator that scales to 1,000 applicants, 12 BigQuery tables, workbench, EMI and FOIR logic, policy agent with clause citations (policy text in files, thresholds editable in the sidebar), mock external services as separate local modules, PDF text reading for uploaded text PDFs, human decision with override reason, fictional delegation of authority, illustrative Key Fact Statement style summary, separate sanction, acceptance and disbursement stages, SQLite audit trail, BigQuery storage of applicants, decisions and audit events, portfolio charts, unit tests.

**Simulated:** all bureau, PAN, bank and fraud responses (mock services); document findings for the built-in cases; sanction and disbursement.

**Not built:** OCR for scanned PDFs, a real Key Fact Statement and cooling-off process, a real fraud service, access control, LLM summaries.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Your default credentials were not found` | Run `gcloud auth application-default login` in the same environment where you run Python, then `gcloud auth application-default set-quota-project YOUR_PROJECT_ID` |
| `module 'data' has no attribute ...` | An old file is being imported. Replace all project files together, delete `__pycache__`, and fully restart Streamlit |
| Sidebar says LOCAL after setting up BigQuery | Read the reason shown after it. Usually `.env` is missing or the load script has not run |
| Load or write fails with a billing message | The sandbox may be blocking writes. Enable billing on the project (free within free-tier limits) |
| Decisions disappear | They are stored in `loan_demo.db`. Deleting that file resets them |

## Data and ethics
All applicants, scores and documents are synthetic. Protected personal characteristics are not used as lending criteria. Policy clauses are fictional and illustrative; they are not RBI requirements or any real bank's policy.

## Run with Docker (optional)
```
docker compose up --build
```
Then open http://localhost:8501. Decisions and the audit trail are kept in a Docker volume. To use BigQuery, set `GCP_PROJECT_ID` and `BQ_DATASET` in your shell or a `.env` file next to `docker-compose.yml`, and uncomment the gcloud volume line in `docker-compose.yml`. Never copy a key file into the image.
