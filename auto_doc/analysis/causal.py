import pandas as pd
from scipy.stats import chi2_contingency, ttest_ind


def treatment_balance(df: pd.DataFrame, treatment_col: str = "treatment") -> dict:
    counts = df[treatment_col].value_counts().sort_index()
    total = int(counts.sum())
    percentages = counts / total * 100
    difference = 0.0
    if 0 in percentages.index and 1 in percentages.index:
        difference = float(abs(percentages.loc[0] - percentages.loc[1]))

    return {
        "counts": counts,
        "percentages": percentages,
        "total": total,
        "difference": difference,
        "has_small_group": bool((counts < 10).any()),
        "is_unbalanced": difference > 40,
    }


def outcome_by_treatment(
    df: pd.DataFrame,
    outcome_col: str,
    treatment_col: str = "treatment",
) -> pd.DataFrame:
    summary = df.groupby(treatment_col)[outcome_col].agg(["mean", "std"])
    summary.columns = ["Media", "Desviacion estandar"]
    return summary


def treatment_ttest(
    df: pd.DataFrame,
    outcome_col: str,
    treatment_col: str = "treatment",
) -> dict:
    group_0 = df[df[treatment_col] == 0][outcome_col]
    group_1 = df[df[treatment_col] == 1][outcome_col]
    t_stat, p_value = ttest_ind(group_0, group_1, equal_var=False)
    return {"t_stat": float(t_stat), "p_value": float(p_value)}


def dag_input_summary(
    df: pd.DataFrame,
    outcome_col: str,
    treatment_col: str = "treatment",
    top_n: int = 5,
    p_threshold: float = 0.05,
) -> dict:
    corr = (
        df.corr(numeric_only=True)[outcome_col]
        .drop(outcome_col)
        .dropna()
        .sort_values(ascending=False)
    )

    confounders = {}
    for col in df.select_dtypes(include="object").columns:
        if col in {treatment_col, outcome_col}:
            continue
        try:
            table = pd.crosstab(df[col], df[treatment_col])
            if table.shape[1] == 2:
                _, p_value, _, _ = chi2_contingency(table)
                if p_value < p_threshold:
                    confounders[col] = round(float(p_value), 5)
        except Exception:
            continue

    return {
        "treatment": treatment_col,
        "outcome": outcome_col,
        "correlaciones": corr.head(top_n).to_dict(),
        "confusoras_categoricas": confounders,
    }
