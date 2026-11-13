import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import LabelEncoder


def diagnostico_causal_df(df: pd.DataFrame, treatment_col: str, backdoor_vars: list) -> dict:
    resultado = {}
    treatment_counts = df[treatment_col].value_counts()
    total = treatment_counts.sum()
    prop_treated = treatment_counts.get(1, 0) / total if 1 in treatment_counts else 0

    resultado["treatment_info"] = {
        "proporcion_tratados": round(prop_treated, 3),
        "n_tratados": int(treatment_counts.get(1, 0)),
        "n_control": int(treatment_counts.get(0, 0)),
    }

    backdoor_info = {}
    treated_df = df[df[treatment_col] == 1]
    control_df = df[df[treatment_col] == 0]

    for var in backdoor_vars:
        if df[var].dtype == "object" or df[var].nunique() < 10:
            try:
                tab = pd.crosstab(df[var], df[treatment_col])
                chi2, _, _, _ = chi2_contingency(tab)
                cramers_v = np.sqrt(chi2 / (total * (min(tab.shape) - 1)))
                backdoor_info[var] = {
                    "tipo": "categorica",
                    "cramers_v": round(cramers_v, 3),
                }
            except Exception:
                continue
        else:
            treated_vals = treated_df[var].dropna()
            control_vals = control_df[var].dropna()
            pooled_std = np.sqrt(((treated_vals.std() ** 2) + (control_vals.std() ** 2)) / 2)
            std_diff = abs(treated_vals.mean() - control_vals.mean()) / pooled_std if pooled_std > 0 else 0
            backdoor_info[var] = {
                "tipo": "numerica",
                "diferencia_media_estandarizada": round(std_diff, 3),
            }

    resultado["backdoor_vars_info"] = backdoor_info

    df_copy = df[backdoor_vars + [treatment_col]].dropna().copy()
    X = df_copy[backdoor_vars]
    y = df_copy[treatment_col]

    X_encoded = X.copy()
    for col in X_encoded.select_dtypes(include="object").columns:
        X_encoded[col] = LabelEncoder().fit_transform(X_encoded[col])

    model = LogisticRegression(solver="liblinear")
    model.fit(X_encoded, y)
    scores = model.predict_proba(X_encoded)[:, 1]

    auc = roc_auc_score(y, scores)
    extremos = np.any((scores < 0.05) | (scores > 0.95))

    resultado["propensity_score"] = {
        "auc": round(auc, 3),
        "extremos": bool(extremos),
        "overlap_visual": "moderado" if 0.1 < scores.mean() < 0.9 else "limitado",
    }

    resultado["recomendaciones_metodologicas"] = {
        "usar_matching": not extremos and auc < 0.85,
        "usar_ipw": not extremos and auc < 0.85,
        "usar_regresion": True,
    }
    return resultado

