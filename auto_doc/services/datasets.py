from pathlib import Path
from typing import Any

import pandas as pd


DATASETS_DIR = Path("auto_doc/files")
SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def ensure_datasets_dir(base_dir: Path = DATASETS_DIR) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def normalize_dataset_name(file_name: str) -> str:
    return Path(file_name).name


def dataset_path(file_name: str, base_dir: Path = DATASETS_DIR) -> Path:
    safe_name = normalize_dataset_name(file_name)
    return ensure_datasets_dir(base_dir) / safe_name


def validate_dataset_extension(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Tipo de archivo no soportado: {suffix}. Extensiones permitidas: {allowed}")
    return suffix


def load_dataset(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    suffix = validate_dataset_extension(path.name)

    if not path.exists():
        raise FileNotFoundError(f"El archivo no existe: {path}")

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".xlsx":
        return pd.read_excel(path)

    raise ValueError(f"Tipo de archivo no soportado: {suffix}")


def save_dataset_bytes(
    file_name: str,
    content: bytes,
    base_dir: Path = DATASETS_DIR,
) -> Path:
    validate_dataset_extension(file_name)
    path = dataset_path(file_name, base_dir)
    path.write_bytes(content)
    return path


def list_datasets(base_dir: Path = DATASETS_DIR) -> list[dict[str, str]]:
    base_dir = ensure_datasets_dir(base_dir)
    datasets = []
    for file_path in sorted(base_dir.glob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            datasets.append({
                "file_name": file_path.name,
                "file_path": str(file_path.resolve()),
            })
    return datasets


def dataset_metadata(df: pd.DataFrame, file_name: str | None = None) -> dict[str, Any]:
    numeric_columns = list(df.select_dtypes(include="number").columns)
    categorical_columns = list(df.select_dtypes(exclude="number").columns)
    missing = df.isna().sum()

    metadata: dict[str, Any] = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "missing_total": int(missing.sum()),
        "duplicated_rows": int(df.duplicated().sum()),
    }
    if file_name:
        metadata["file_name"] = file_name
    return metadata
