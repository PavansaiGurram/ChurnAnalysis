"""Run the telecom customer churn analysis and write reproducible outputs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "datatelco_churn.csv"
OUTPUT_DIR = ROOT / "outputs"
DATABASE_PATH = OUTPUT_DIR / "churn.db"

REQUIRED_COLUMNS = {
    "customerID",
    "tenure",
    "Contract",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
}


def prepare_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the source data and return cleaned records and a quality summary."""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    source = pd.read_csv(DATA_PATH)
    missing_columns = REQUIRED_COLUMNS.difference(source.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")

    raw_rows = len(source)
    duplicate_ids = int(source["customerID"].duplicated().sum())
    blank_total_charges = source["TotalCharges"].astype("string").str.strip().eq("").sum()

    df = source.copy()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    for column in ("tenure", "MonthlyCharges"):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_before = df.isna().sum()
    invalid_tenure = int((df["tenure"].lt(0) | df["tenure"].gt(120)).sum())
    invalid_monthly_charges = int(df["MonthlyCharges"].lt(0).sum())
    required_for_analysis = ["customerID", "Churn", "tenure", "MonthlyCharges"]
    rows_missing_required = int(df[required_for_analysis].isna().any(axis=1).sum())

    # Rows without a customer ID or churn label cannot be analyzed reliably.
    df = df.dropna(subset=required_for_analysis).copy()
    df = df.drop_duplicates(subset="customerID", keep="first").copy()

    df["Churn"] = df["Churn"].astype("string").str.strip().str.title()
    unexpected_churn = sorted(set(df["Churn"].dropna()) - {"Yes", "No"})
    if unexpected_churn:
        raise ValueError(f"Unexpected Churn values: {unexpected_churn}")
    df["churn_flag"] = df["Churn"].eq("Yes").astype("int64")

    df["tenure_group"] = pd.cut(
        df["tenure"],
        bins=[-1, 12, 24, 48, 72, float("inf")],
        labels=["0-12 months", "13-24 months", "25-48 months", "49-72 months", "73+ months"],
        right=True,
    ).astype("string")
    df["monthly_charge_band"] = pd.cut(
        df["MonthlyCharges"],
        bins=[-float("inf"), 35, 70, 90, float("inf")],
        labels=["Under $35", "$35-$70", "$70-$90", "Over $90"],
        right=True,
    ).astype("string")

    # An interpretable prioritization heuristic, not a trained probability model.
    high_risk = df["Contract"].eq("Month-to-month") & df["tenure"].le(12)
    medium_risk = (
        df["Contract"].eq("Month-to-month")
        | df["tenure"].le(24)
        | df["PaymentMethod"].eq("Electronic check")
    )
    df["risk_segment"] = "Low"
    df.loc[medium_risk, "risk_segment"] = "Medium"
    df.loc[high_risk, "risk_segment"] = "High"

    quality_rows = [
        ("source_rows", raw_rows, "Rows present in the source CSV"),
        ("analysis_rows", len(df), "Rows retained for churn analysis"),
        ("rows_missing_required_fields", rows_missing_required, "Dropped before analysis"),
        ("duplicate_customer_ids", duplicate_ids, "Keep first record per customer ID if any exist"),
        ("blank_total_charges", int(blank_total_charges), "Retained as missing"),
        ("invalid_tenure_outside_0_to_120", invalid_tenure, "Reported; investigate if non-zero"),
        ("negative_monthly_charges", invalid_monthly_charges, "Reported; investigate if non-zero"),
    ]
    for column, count in missing_before.items():
        if count:
            quality_rows.append(
                (f"missing_{column}", int(count), "Not imputed; inspect before modeling")
            )
    for column in ("MonthlyCharges", "TotalCharges"):
        values = df[column].dropna()
        if not values.empty:
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            outlier_count = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
            quality_rows.append(
                (f"iqr_outliers_{column}", outlier_count, "Retained; investigate, not automatically removed")
            )
    quality = pd.DataFrame(quality_rows, columns=["check", "count", "handling"])
    return df, quality


def summarize(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create the segment tables used by the SQL and chart outputs."""
    grouped_columns = {
        "contract": "Contract",
        "tenure": "tenure_group",
        "monthly_charges": "monthly_charge_band",
        "risk": "risk_segment",
    }
    summaries: dict[str, pd.DataFrame] = {}
    for key, column in grouped_columns.items():
        table = (
            df.groupby(column, observed=False)
            .agg(customers=("customerID", "count"), churned=("churn_flag", "sum"))
            .reset_index()
            .rename(columns={column: "segment"})
        )
        table["churn_rate_pct"] = (100 * table["churned"] / table["customers"]).round(2)
        summaries[key] = table

    summaries["overall"] = pd.DataFrame(
        [
            {
                "customers": len(df),
                "churned": int(df["churn_flag"].sum()),
                "churn_rate_pct": round(float(df["churn_flag"].mean() * 100), 2),
                "average_monthly_charges": round(float(df["MonthlyCharges"].mean()), 2),
                "median_tenure_months": round(float(df["tenure"].median()), 1),
            }
        ]
    )
    return summaries


def save_charts(df: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> None:
    """Save readable churn comparison charts to outputs/charts."""
    charts_dir = OUTPUT_DIR / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    colors = {"Yes": "#d95f5f", "No": "#4c78a8"}

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    churn_mix = df["Churn"].value_counts().reindex(["No", "Yes"], fill_value=0)
    axes[0, 0].bar(churn_mix.index, churn_mix.values, color=[colors["No"], colors["Yes"]])
    axes[0, 0].set(title="Customer churn outcome", ylabel="Customers")

    contract = summaries["contract"].sort_values("churn_rate_pct", ascending=False)
    axes[0, 1].bar(contract["segment"], contract["churn_rate_pct"], color="#e08b50")
    axes[0, 1].set(title="Churn rate by contract", ylabel="Churn rate (%)")
    axes[0, 1].tick_params(axis="x", rotation=15)

    tenure = summaries["tenure"].dropna()
    axes[1, 0].bar(tenure["segment"], tenure["churn_rate_pct"], color="#72a879")
    axes[1, 0].set(title="Churn rate by tenure", ylabel="Churn rate (%)")
    axes[1, 0].tick_params(axis="x", rotation=15)

    risk_order = ["High", "Medium", "Low"]
    risk = summaries["risk"].set_index("segment").reindex(risk_order).dropna()
    axes[1, 1].bar(risk.index, risk["churn_rate_pct"], color=["#c94c4c", "#e7a44a", "#6a9f78"])
    axes[1, 1].set(title="Churn rate by heuristic risk segment", ylabel="Churn rate (%)")

    for axis in axes.flat:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    fig.suptitle("Telecom customer churn overview", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(charts_dir / "churn_overview.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    churn_yes = df.loc[df["Churn"].eq("Yes"), "MonthlyCharges"]
    churn_no = df.loc[df["Churn"].eq("No"), "MonthlyCharges"]
    ax.boxplot([churn_no, churn_yes], tick_labels=["Stayed", "Churned"], showfliers=False)
    ax.set(title="Monthly charges by churn outcome", ylabel="Monthly charges ($)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(charts_dir / "monthly_charges_by_churn.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def write_summary(summaries: dict[str, pd.DataFrame], quality: pd.DataFrame) -> None:
    """Write a short, data-driven narrative for the project deliverable."""
    overall = summaries["overall"].iloc[0]
    contract = summaries["contract"].sort_values("churn_rate_pct", ascending=False)
    tenure = summaries["tenure"].dropna().sort_values("churn_rate_pct", ascending=False)
    charges = summaries["monthly_charges"].sort_values("churn_rate_pct", ascending=False)
    risk = summaries["risk"].set_index("segment")
    top_contract = contract.iloc[0]
    top_charge_band = charges.iloc[0]
    early_tenure = tenure.loc[tenure["segment"].eq("0-12 months")].head(1)
    missing_total = int(quality.loc[quality["check"].eq("missing_TotalCharges"), "count"].sum())

    lines = [
        "# Customer churn analysis: findings",
        "",
        "## Snapshot",
        "",
        f"- Analyzed **{int(overall['customers']):,}** customers; **{int(overall['churned']):,}** churned.",
        f"- Overall churn rate: **{overall['churn_rate_pct']:.2f}%**.",
        f"- Average monthly charge: **${overall['average_monthly_charges']:.2f}**; "
        f"median tenure: **{overall['median_tenure_months']:.0f} months**.",
        f"- Highest-churn contract segment: **{top_contract['segment']}** "
        f"({top_contract['churn_rate_pct']:.2f}%).",
        f"- Highest-churn monthly-charge band: **{top_charge_band['segment']}** "
        f"({top_charge_band['churn_rate_pct']:.2f}%).",
    ]
    if not early_tenure.empty:
        lines.append(
            f"- Customers in their first 12 months churn at "
            f"**{early_tenure.iloc[0]['churn_rate_pct']:.2f}%**."
        )
    lines.extend(
        [
            "",
            "## Retention recommendations",
            "",
            "1. Prioritize proactive onboarding and service check-ins during the first year, "
            "when early-tenure churn is elevated.",
            "2. Offer suitable longer-term plans to month-to-month customers; test offers with "
            "controlled experiments and monitor margin as well as retention.",
            "3. Review perceived value and service fit for customers in higher-churn charge bands; "
            "the association does not establish that price causes churn.",
            "4. Use the High/Medium/Low segments as a transparent outreach queue, not as "
            "individual churn probabilities. Validate campaign impact before scaling.",
            "",
            "## Data quality notes",
            "",
            f"- {missing_total} `TotalCharges` values are blank/non-numeric; they correspond to "
            "zero-tenure customers in this source and remain missing rather than being imputed.",
            "- Outliers are assessed with IQR summaries and retained; unusual charges may be valid "
            "customer behavior, not data errors.",
            "- The risk segment is an explicitly defined heuristic based on contract, tenure, and "
            "payment method; this project does not train a predictive model.",
            "",
            "## Risk segment results",
            "",
            "| Segment | Customers | Churned | Churn rate |",
            "|---|---:|---:|---:|",
        ]
    )
    for segment in ("High", "Medium", "Low"):
        row = risk.loc[segment]
        lines.append(
            f"| {segment} | {int(row['customers']):,} | {int(row['churned']):,} | "
            f"{row['churn_rate_pct']:.2f}% |"
        )
    (OUTPUT_DIR / "findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, quality = prepare_data()
    summaries = summarize(df)

    # Normalize field names for a consistent SQL interface.
    sql_df = df.rename(
        columns={
            "customerID": "customer_id",
            "SeniorCitizen": "senior_citizen",
            "MonthlyCharges": "monthly_charges",
            "TotalCharges": "total_charges",
            "Churn": "churn",
            "Contract": "contract",
            "PaymentMethod": "payment_method",
            "tenure": "tenure",
        }
    )
    sql_df.to_csv(OUTPUT_DIR / "cleaned_customers.csv", index=False)
    quality.to_csv(OUTPUT_DIR / "data_quality.csv", index=False)
    for name, table in summaries.items():
        table.to_csv(OUTPUT_DIR / f"{name}_summary.csv", index=False)

    with sqlite3.connect(DATABASE_PATH) as connection:
        sql_df.to_sql("customers", connection, if_exists="replace", index=False)
        quality.to_sql("data_quality", connection, if_exists="replace", index=False)

    save_charts(df, summaries)
    write_summary(summaries, quality)

    print(f"Analyzed {len(df):,} customers; churn rate: {summaries['overall'].iloc[0]['churn_rate_pct']:.2f}%")
    print(f"Outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
