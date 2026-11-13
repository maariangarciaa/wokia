import re
import unicodedata


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def build_graph_context(df):
    numeric_columns = list(df.select_dtypes(include="number").columns)
    return (
        f"Columnas disponibles: {list(df.columns)}\n"
        f"Columnas numericas disponibles: {numeric_columns}\n"
        f"Tipos de datos:\n{df.dtypes.astype(str).to_string()}\n"
        f"Primeras filas:\n{df.head(3).to_markdown(index=False)}"
    )


def build_chart_fallback(user_input, df):
    text = normalize_text(user_input)
    numeric_columns = list(df.select_dtypes(include="number").columns)
    pink = "rosa" in text or "pink" in text

    if "correlacion" in text or "correlation" in text:
        cmap = "RdPu" if pink else "coolwarm"
        return f"""
```python
numeric_df = df[{numeric_columns!r}]
corr = numeric_df.corr(numeric_only=True)
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(corr, annot=True, cmap='{cmap}', center=0, fmt='.2f', linewidths=0.5, ax=ax)
_ = ax.set_title('Correlation matrix')
_ = ax.tick_params(axis='x', rotation=45)
_ = ax.tick_params(axis='y', rotation=0)
```
"""

    if "boxplot" in text or "diagrama de caja" in text or "caja" in text:
        color = "#F4A6C1" if pink else "#A4C6E8"
        y_col = "PriceEuro" if "PriceEuro" in df.columns else numeric_columns[0]
        x_col = "BodyStyle" if "BodyStyle" in df.columns else df.select_dtypes(exclude="number").columns[0]
        return f"""
```python
fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(data=df, x='{x_col}', y='{y_col}', color='{color}', ax=ax)
_ = ax.set_title('{y_col} by {x_col}')
_ = ax.set_xlabel('{x_col}')
_ = ax.set_ylabel('{y_col}')
_ = ax.tick_params(axis='x', rotation=45)
```
"""

    return None


def sanitize_generated_code(code: str, user_input: str) -> str:
    text = normalize_text(user_input)
    cleaned = re.sub(r"plt\.show\(\)\s*;?", "", code)
    cleaned = re.sub(r"\.show\(\)\s*;?", "", cleaned)

    # Seaborn expects a palette name/list for `palette`, not a single hex color.
    cleaned = re.sub(r"palette\s*=\s*['\"]#([0-9A-Fa-f]{6})['\"]", r"color='#\1'", cleaned)

    if "rosa" in text or "pink" in text:
        cleaned = re.sub(r"color\s*=\s*['\"]#A4C6E8['\"]", "color='#F4A6C1'", cleaned)

    if ("correlacion" in text or "correlation" in text) and ("rosa" in text or "pink" in text):
        cleaned = re.sub(r"cmap\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)
        cleaned = re.sub(r"palette\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)
        if "sns.heatmap" in cleaned and "cmap=" not in cleaned:
            cleaned = re.sub(r"sns\.heatmap\(([^,\n\)]+),", r"sns.heatmap(\1, cmap='RdPu',", cleaned, count=1)

    if "correlacion" in user_input.lower():
        if "rosa" in user_input.lower() or "pink" in user_input.lower():
            cleaned = re.sub(r"cmap\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)
            cleaned = re.sub(r"palette\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)

    return cleaned
