# Customer churn analysis: findings

## Snapshot

- Analyzed **7,043** customers; **1,869** churned.
- Overall churn rate: **26.54%**.
- Average monthly charge: **$64.76**; median tenure: **29 months**.
- Highest-churn contract segment: **Month-to-month** (42.71%).
- Highest-churn monthly-charge band: **$70-$90** (37.80%).
- Customers in their first 12 months churn at **47.44%**.

## Retention recommendations

1. Prioritize proactive onboarding and service check-ins during the first year, when early-tenure churn is elevated.
2. Offer suitable longer-term plans to month-to-month customers; test offers with controlled experiments and monitor margin as well as retention.
3. Review perceived value and service fit for customers in higher-churn charge bands; the association does not establish that price causes churn.
4. Use the High/Medium/Low segments as a transparent outreach queue, not as individual churn probabilities. Validate campaign impact before scaling.

## Data quality notes

- 11 `TotalCharges` values are blank/non-numeric; they correspond to zero-tenure customers in this source and remain missing rather than being imputed.
- Outliers are assessed with IQR summaries and retained; unusual charges may be valid customer behavior, not data errors.
- The risk segment is an explicitly defined heuristic based on contract, tenure, and payment method; this project does not train a predictive model.

## Risk segment results

| Segment | Customers | Churned | Churn rate |
|---|---:|---:|---:|
| High | 1,994 | 1,024 | 51.35% |
| Medium | 2,826 | 731 | 25.87% |
| Low | 2,223 | 114 | 5.13% |
