# Fictional Bank: Agentic AI Personal Loan Approval Workbench

> **Proof of concept using synthetic data only.** The bank is fictional. Nothing here is a real lending decision, and an AI recommendation is **not** a sanction or a legally binding decision. No real bureau, KYC, Aadhaar, PAN or RBI system is called.

A Streamlit demo of how agentic AI could support retail personal loan approval at a mid-sized Indian bank, while keeping a human credit officer in control. It was built for a Business Analyst (Data and AI Presales) assignment.

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

The other 294 applicants are generated with a fixed random seed, so results are repeatable.

## How decisions are made
- **Document agent:** checks mandatory documents (PAN, salary slip, bank statement) and name consistency against a mock PAN record.
- **Credit and affordability agent:** reads a mock bureau score and computes the proposed EMI with the standard amortisation formula. Fixed obligations to income (FOIR) is defined as `(existing EMIs + proposed EMI) / gross monthly income`.
- **Policy agent:** retrieves the matching clause from 8 illustrative policy clauses by keyword overlap (no vector database) and applies plain Python rules, citing the clause for every result.
- **Recommendation agent:** combines the findings into one of: approve for consideration, refer, or decline recommendation.
- **Credit officer:** records Approve, Decline or Request information. Disagreeing with the recommendation requires a written reason. Approval leads to three separate steps: sanction terms, customer acceptance, disbursement.

No LLM is used, and no API key is required. Thresholds (illustrative bank settings, **not RBI rules**) are in `policy.py`: age 21 to 60, 2 years employment, score decline below 680 and review below 720, FOIR decline above 50% and review above 40%, loan up to 12 times monthly income.

## Optional: BigQuery
1. Create a Google Cloud project and a BigQuery dataset.
2. Run `gcloud auth application-default login` (the command must contain `application-default`).
3. Copy `.env.example` to `.env` and set `GCP_PROJECT_ID` and `BQ_DATASET`. Never commit `.env`.
4. Run `python load_to_bigquery.py`. It creates the tables and uploads 300 synthetic applicants.
5. Restart the app. The sidebar turns green only when BigQuery is actually used.

Tables created: `applicants`, `decisions`, `audit_events`. Decisions and audit events are saved to local SQLite first and copied to BigQuery on a best-effort basis. Set `BQ_MIRROR=false` to turn the copy off.
The free BigQuery sandbox may block writes and expires tables after 60 days. Enabling billing stays free within the free-tier limits.

## Project structure
```
app.py                  Streamlit UI, four pages, agent orchestration
policy.py               Policy agent: illustrative clauses, retrieval, rules
logic.py                EMI and FOIR calculations
data.py                 Synthetic data generator, SQLite persistence, data source selection
bq.py                   Optional BigQuery layer
load_to_bigquery.py     One-off table creation and upload
tests/                  Unit tests
docs/                   Documentation required during submission
requirements.txt        Dependencies
.env.example            Configuration template (no secrets)
```

## Tests
```
pip install pytest
pytest
```

## What is implemented, simulated and not built
**Implemented:** workbench, EMI and FOIR logic, policy agent with clause citations, human decision with override reason, separate sanction, acceptance and disbursement stages, SQLite audit trail, BigQuery storage of applicants, decisions and audit events, unit tests.

**Simulated:** document checks (file names and a mock PAN name only; PDFs are not read), bureau and identity responses, sanction and disbursement. These are inline mock values, not separate services.

**Not built:** PDF text extraction or OCR, separate mock API services with failure cases, a fraud screening service, Key Fact Statement and cooling-off handling, delegation of authority by loan size, access control, LLM summaries, and the remaining BigQuery tables (accounts, transactions, bureau results).

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
