from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ManualTreatmentResult:
    df_tratado: pd.DataFrame
    treatment_col: str
    source_col: str
    value_1: Any
    value_0: Any
    was_binary: bool


@dataclass
class OutcomePreparationResult:
    df_tratado: pd.DataFrame
    outcome_col: str
    is_valid: bool
    was_converted: bool
    value_1: Any = None
    value_0: Any = None


def create_manual_treatment(
    df: pd.DataFrame,
    treatment_source_col: str,
    treatment_col: str = "treatment",
) -> ManualTreatmentResult:
    values = df[treatment_source_col].dropna().unique()
    was_binary = len(values) == 2

    value_1 = df[treatment_source_col].mode()[0]
    value_0 = [value for value in values if value != value_1][0] if was_binary else f"!={value_1}"

    df_tratado = df.copy()
    df_tratado[treatment_col] = df_tratado[treatment_source_col].apply(
        lambda value: 1 if value == value_1 else 0
    )

    return ManualTreatmentResult(
        df_tratado=df_tratado,
        treatment_col=treatment_col,
        source_col=treatment_source_col,
        value_1=value_1,
        value_0=value_0,
        was_binary=was_binary,
    )


def prepare_outcome(
    df_original: pd.DataFrame,
    df_tratado: pd.DataFrame,
    outcome_col: str,
) -> OutcomePreparationResult:
    values = df_original[outcome_col].dropna().unique()

    if df_original[outcome_col].dtype.kind in "ifu":
        return OutcomePreparationResult(
            df_tratado=df_tratado,
            outcome_col=outcome_col,
            is_valid=True,
            was_converted=False,
        )

    if len(values) != 2:
        return OutcomePreparationResult(
            df_tratado=df_tratado,
            outcome_col=outcome_col,
            is_valid=False,
            was_converted=False,
        )

    value_1 = df_original[outcome_col].mode()[0]
    value_0 = [value for value in values if value != value_1][0]
    converted_df = df_tratado.copy()
    was_converted = set(values) != {0, 1}

    if was_converted:
        converted_df[outcome_col] = df_original[outcome_col].apply(
            lambda value: 1 if value == value_1 else 0
        )

    return OutcomePreparationResult(
        df_tratado=converted_df,
        outcome_col=outcome_col,
        is_valid=True,
        was_converted=was_converted,
        value_1=value_1,
        value_0=value_0,
    )
