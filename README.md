# Telecom customer churn analysis

An end-to-end exploratory analysis of the included telecom customer CSV using Python, SQLite, and matplotlib. The workflow validates the source, creates interpretable churn segments, compares churn by contract/tenure/monthly charges, saves charts and tables, and writes a data-driven retention summary.

## Run

From the project folder:

```powershell
python -m pip install -r requirements.txt
python analyze_churn.py
```

The script reads `data/datatelco_churn.csv` relative to its own location, so it can be started from any working directory. Open `churn.ipynb` to explore the same analysis interactively.

## Outputs

- `outputs/churn.db` — SQLite database with `customers` and `data_quality` tables.
- `outputs/cleaned_customers.csv` and `outputs/data_quality.csv` — analysis-ready records and quality checks.
- `outputs/*_summary.csv` — overall, contract, tenure, monthly-charge, and risk-segment summaries.
- `outputs/charts/churn_overview.png` and `outputs/charts/monthly_charges_by_churn.png` — visual comparisons.
- `outputs/findings.md` — automatically generated summary and retention recommendations.
- `sql/analysis.sql` — corresponding SQLite queries.

## Data handling and scope

Blank `TotalCharges` values are converted to missing values. The included data has these blanks on zero-tenure customers; they are kept and not imputed. Duplicate customer IDs are reported and deduplicated by retaining the first record. Charge outliers are reported/visualized but not removed because unusual amounts may be legitimate. Missing values in required analysis fields and unexpected churn labels are handled explicitly.

The risk segment is a transparent prioritization heuristic: High means month-to-month and tenure at most 12 months; Medium means month-to-month, tenure at most 24 months, or electronic-check payment; all others are Low. It is not a trained model and its segment churn rate is not an individual probability. Recommendations are exploratory associations, not causal claims.

## Dataset

The analysis uses the public IBM Telco Customer Churn dataset distributed in this project as `data/datatelco_churn.csv`.
