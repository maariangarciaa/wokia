import pandas as pd


def _json_safe(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _series_summary(series: pd.Series) -> dict:
    non_null = series.dropna()
    summary = {
        "name": series.name,
        "dtype": str(series.dtype),
        "missing": int(series.isna().sum()),
        "missing_pct": round(float(series.isna().mean() * 100), 2),
        "unique": int(series.nunique(dropna=True)),
    }

    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(non_null, errors="coerce").dropna()
        summary["kind"] = "numeric"
        summary["stats"] = {
            "mean": _json_safe(round(numeric.mean(), 4)) if not numeric.empty else None,
            "std": _json_safe(round(numeric.std(), 4)) if len(numeric) > 1 else None,
            "min": _json_safe(numeric.min()) if not numeric.empty else None,
            "p25": _json_safe(numeric.quantile(0.25)) if not numeric.empty else None,
            "median": _json_safe(numeric.median()) if not numeric.empty else None,
            "p75": _json_safe(numeric.quantile(0.75)) if not numeric.empty else None,
            "max": _json_safe(numeric.max()) if not numeric.empty else None,
        }
    elif pd.api.types.is_bool_dtype(series):
        summary["kind"] = "boolean"
        summary["top_values"] = {
            str(key): int(value)
            for key, value in series.value_counts(dropna=True).head(5).items()
        }
    elif pd.api.types.is_datetime64_any_dtype(series):
        summary["kind"] = "datetime"
        summary["stats"] = {
            "min": str(non_null.min()) if not non_null.empty else None,
            "max": str(non_null.max()) if not non_null.empty else None,
        }
    else:
        summary["kind"] = "categorical"
        summary["top_values"] = {
            str(key): int(value)
            for key, value in series.value_counts(dropna=True).head(5).items()
        }

    return summary


def dataset_profile(df: pd.DataFrame, file_name: str | None = None, preview_rows: int = 10) -> dict:
    numeric_df = df.select_dtypes(include="number")
    missing = df.isna().sum()

    profile = {
        "file_name": file_name,
        "shape": {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
        },
        "columns": [_series_summary(df[column]) for column in df.columns],
        "missing_total": int(missing.sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": list(numeric_df.columns),
        "categorical_columns": list(df.select_dtypes(exclude="number").columns),
        "preview": df.head(preview_rows).where(pd.notna(df.head(preview_rows)), None).to_dict(orient="records"),
    }

    if numeric_df.empty:
        profile["numeric_summary"] = {}
        profile["correlations"] = {}
    else:
        profile["numeric_summary"] = (
            numeric_df.describe()
            .round(4)
            .where(pd.notna(numeric_df.describe()), None)
            .to_dict()
        )
        if numeric_df.shape[1] >= 2:
            profile["correlations"] = (
                numeric_df.corr(numeric_only=True)
                .round(4)
                .where(pd.notna(numeric_df.corr(numeric_only=True)), None)
                .to_dict()
            )
        else:
            profile["correlations"] = {}

    return profile


def build_dataset_context(df: pd.DataFrame) -> str:
    """Return a compact textual context for LLM-assisted dataset profiling."""
    numeric_df = df.select_dtypes(include="number")
    missing = df.isna().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    duplicated_count = int(df.duplicated().sum())

    context_parts = [
        f"Dimensiones: {len(df)} filas y {len(df.columns)} columnas.",
        f"Columnas: {list(df.columns)}",
        f"Tipos de datos:\n{df.dtypes.astype(str).to_string()}",
        f"Primeras filas:\n{df.head(5).to_markdown(index=False)}",
        f"Valores nulos por columna:\n{pd.DataFrame({'nulos': missing, 'porcentaje': missing_pct}).to_markdown()}",
        f"Numero de filas duplicadas exactas: {duplicated_count}",
    ]

    if not numeric_df.empty:
        context_parts.append(f"Resumen numerico:\n{numeric_df.describe().round(2).to_markdown()}")
    if numeric_df.shape[1] >= 2:
        context_parts.append(f"Matriz de correlacion numerica:\n{numeric_df.corr(numeric_only=True).round(2).to_markdown()}")

    return "\n\n".join(context_parts)


def summarize_missing_values(df: pd.DataFrame) -> str:
    missing = df.isna().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_table = pd.DataFrame({
        "columna": missing.index,
        "nulos": missing.values,
        "porcentaje": missing_pct.values,
    })
    missing_table = missing_table[missing_table["nulos"] > 0]

    if missing_table.empty:
        return "No se detectan valores nulos en ninguna columna."

    missing_table = missing_table.sort_values(["porcentaje", "nulos"], ascending=False)
    rows = ["| Columna | Nulos | Porcentaje |", "|---|---:|---:|"]
    for _, row in missing_table.iterrows():
        col_name = f"`{row['columna']}`"
        if row["porcentaje"] >= 10:
            col_name = f"**{col_name}**"
        rows.append(f"| {col_name} | {int(row['nulos'])} | {row['porcentaje']:.2f}% |")

    return "\n".join(rows)


def summarize_duplicates(df: pd.DataFrame) -> str:
    duplicated_mask = df.duplicated(keep=False)
    if not duplicated_mask.any():
        return "No se detectan registros duplicados exactos."

    duplicated_rows = df.loc[duplicated_mask].drop_duplicates()
    total = int(df.duplicated().sum())
    header = f"Se detectan {total} registros duplicados exactos. Filas duplicadas unicas:"
    impact = "Estos duplicados pueden inflar frecuencias, sesgar medias o dar mas peso a observaciones repetidas durante el analisis."
    return f"{header}\n\n{duplicated_rows.to_markdown(index=False)}\n\n{impact}"
