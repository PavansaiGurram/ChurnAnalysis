-- Run after analyze_churn.py creates outputs/churn.db.
-- SQLite table: customers; churn_flag is 1 for churned and 0 for retained.

-- Overall churn rate
SELECT
    COUNT(*) AS customers,
    SUM(churn_flag) AS churned,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 2) AS churn_rate_pct
FROM customers;

-- Compare churn rates by contract
SELECT
    contract,
    COUNT(*) AS customers,
    SUM(churn_flag) AS churned,
    ROUND(100.0 * AVG(churn_flag), 2) AS churn_rate_pct
FROM customers
GROUP BY contract
ORDER BY churn_rate_pct DESC;

-- Compare churn rates by tenure group
SELECT
    tenure_group,
    COUNT(*) AS customers,
    SUM(churn_flag) AS churned,
    ROUND(100.0 * AVG(churn_flag), 2) AS churn_rate_pct
FROM customers
GROUP BY tenure_group
ORDER BY MIN(tenure);

-- Compare churn rates by monthly charge band
SELECT
    monthly_charge_band,
    COUNT(*) AS customers,
    SUM(churn_flag) AS churned,
    ROUND(100.0 * AVG(churn_flag), 2) AS churn_rate_pct
FROM customers
GROUP BY monthly_charge_band
ORDER BY MIN(monthly_charges);

-- Prioritization segments (heuristic, not predicted probabilities)
SELECT
    risk_segment,
    COUNT(*) AS customers,
    SUM(churn_flag) AS churned,
    ROUND(100.0 * AVG(churn_flag), 2) AS churn_rate_pct
FROM customers
GROUP BY risk_segment
ORDER BY CASE risk_segment WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;

-- Check database quality metadata
SELECT "check", count, handling
FROM data_quality
ORDER BY "check";
