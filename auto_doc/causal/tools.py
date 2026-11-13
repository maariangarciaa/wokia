import ast
import json
import re

import pandas as pd
import streamlit as st
from langchain.agents import Tool
from langchain_experimental.tools.python.tool import PythonAstREPLTool

from auto_doc.causal.dag import generate_dag
from auto_doc.causal.diagnostics import diagnostico_causal_df


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def identify_causal_effect(*args, **kwargs):
    model = st.session_state["causal_model"]
    estimand = model.identify_effect()
    st.session_state["identified_estimand"] = estimand
    backdoors = estimand.get_backdoor_variables()
    return f"{estimand}\n\nBackdoor variables: {backdoors}"


def make_diagnostico_tool(df: pd.DataFrame):
    def diagnostico_tool_wrapped(input: str) -> dict:
        try:
            cleaned_input = str(input).strip()
            fenced = re.search(r"```(?:json|python)?\s*(.*?)\s*```", cleaned_input, re.DOTALL)
            if fenced:
                cleaned_input = fenced.group(1).strip()

            dict_match = re.search(r"\{.*\}", cleaned_input, re.DOTALL)
            if dict_match:
                cleaned_input = dict_match.group(0).strip()

            params = ast.literal_eval(cleaned_input)
            treatment_col = params["treatment_col"]
            backdoor_vars = params["backdoor_vars"]
            return diagnostico_causal_df(df, treatment_col, backdoor_vars)
        except Exception as e:
            raise ValueError(f"Error al ejecutar diagnostico causal: {e}")

    return Tool.from_function(
        func=diagnostico_tool_wrapped,
        name="diagnostico_causal_df_tool",
        description="Diagnostico de balance y score de propension. Requiere un dict con: 'treatment_col' y 'backdoor_vars'. El DataFrame ya esta disponible como `df` interno.",
    )


def make_python_repl_tool(df: pd.DataFrame):
    python_repl = PythonAstREPLTool(locals={"df": df})

    def repair_common_inline_loop(code: str) -> str:
        match = re.search(
            r"objetivo\s*=\s*None\s*;\s*for\s+(\w+)\s+in\s+df\.columns\s*:\s*if\s+(.+?)\s*:\s*objetivo\s*=\s*\1\s*;\s*print\(objetivo\)",
            code,
            flags=re.IGNORECASE,
        )
        if not match:
            return code

        loop_var = match.group(1)
        condition = match.group(2).strip()
        return (
            "objetivo = None\n"
            f"for {loop_var} in df.columns:\n"
            f"    if {condition}:\n"
            f"        objetivo = {loop_var}\n"
            "print(objetivo)"
        )

    def run_python_on_df(code: str) -> str:
        cleaned_code = str(code).strip()

        if cleaned_code.startswith("```"):
            cleaned_code = re.sub(r"^```(?:python)?\s*", "", cleaned_code)
            cleaned_code = re.sub(r"\s*```$", "", cleaned_code)

        if cleaned_code.startswith("`") and cleaned_code.endswith("`"):
            cleaned_code = cleaned_code[1:-1].strip()

        if cleaned_code.lower().startswith("python\n"):
            cleaned_code = cleaned_code.split("\n", 1)[1].strip()

        forbidden_patterns = [
            r"\bdf\s*=",
            r"\bdf\s*:\s*",
            r"pd\.DataFrame\s*\(",
            r"pandas\.DataFrame\s*\(",
        ]
        if any(re.search(pattern, cleaned_code) for pattern in forbidden_patterns):
            return (
                "No puedes crear ni sobrescribir `df`. El DataFrame real ya existe. "
                "Consulta su contenido con expresiones como `df.shape`, `df.dtypes`, "
                "`df.head()`, `df.isna().sum()` o `df.describe()`."
            )

        if cleaned_code.startswith("{") and cleaned_code.endswith("}"):
            return (
                "Ese JSON ya es una respuesta final, no una accion Python. "
                "No vuelvas a ejecutar esta herramienta; devuelve ese contenido como `Final Answer:`."
            )

        cleaned_code = repair_common_inline_loop(cleaned_code)

        try:
            ast.parse(cleaned_code)
        except SyntaxError as error:
            return (
                f"SyntaxError en Action Input: {error.msg}. "
                "No repitas el mismo codigo. Usa expresiones Python simples, por ejemplo: "
                "list(df.columns), df.dtypes, df.select_dtypes(include='number').columns.tolist(), "
                "o next((col for col in df.columns if 'PriceEuro' in col), None)."
            )

        return python_repl.run(cleaned_code)

    return Tool.from_function(
        func=run_python_on_df,
        name="python_repl_ast",
        description=(
            "Ejecuta Python sobre el DataFrame real ya cargado como `df`. "
            "Action Input debe ser codigo Python puro, sin backticks, sin Markdown y sin crear `df`. "
            "Usa esta herramienta para consultar `df.shape`, `df.dtypes`, `df.columns`, `df.head()` y calculos derivados."
        ),
    )


def make_candidate_variables_tool(df: pd.DataFrame):
    def find_candidate_variables(question: str) -> str:
        question_text = str(question).lower()
        numeric_columns = df.select_dtypes(include="number").columns.tolist()

        target = None
        for column in df.columns:
            if column.lower() in question_text:
                target = column
                break

        if target is None:
            aliases = {
                "precio": ["price", "precio", "coste", "costo"],
                "velocidad": ["speed", "velocidad"],
                "autonomia": ["range", "autonomia", "autonomia"],
                "eficiencia": ["efficiency", "eficiencia"],
            }
            for words in aliases.values():
                matches = [
                    column
                    for column in df.columns
                    if any(word in column.lower() for word in words)
                    and any(word in question_text for word in words)
                ]
                if matches:
                    target = matches[0]
                    break

        if target is None:
            return json.dumps(
                {
                    "error": "No se pudo identificar una variable objetivo en la pregunta.",
                    "columnas_disponibles": list(df.columns),
                },
                ensure_ascii=False,
            )

        if target not in numeric_columns:
            return json.dumps(
                {
                    "objetivo": target,
                    "candidatas": [],
                    "aviso": "La variable objetivo identificada no es numerica; no se calcularon correlaciones.",
                },
                ensure_ascii=False,
            )

        correlations = (
            df[numeric_columns]
            .corr(numeric_only=True)[target]
            .drop(labels=[target], errors="ignore")
            .dropna()
            .sort_values(key=lambda series: series.abs(), ascending=False)
        )
        candidates = correlations[correlations.abs() > 0.7].index.tolist()

        return json.dumps(
            {
                "objetivo": target,
                "candidatas": candidates,
                "correlaciones": {key: round(float(value), 4) for key, value in correlations.items()},
            },
            ensure_ascii=False,
        )

    return Tool.from_function(
        func=find_candidate_variables,
        name="find_candidate_variables",
        description=(
            "Identifica la variable objetivo mencionada en una pregunta causal y calcula en una sola accion "
            "las variables numericas candidatas con correlacion fuerte. Input: pregunta causal del usuario. "
            "Devuelve JSON valido con objetivo, candidatas y correlaciones."
        ),
    )


def estimate_causal_effect_tool(input: str = "") -> str:
    try:
        model = st.session_state.get("causal_model")
        estimand = st.session_state.get("identified_estimand")
        metodo = st.session_state.get("metodo_seleccionado")

        if model is None or estimand is None or metodo is None:
            return json.dumps({
                "error": "Faltan elementos clave: modelo causal, estimand o metodo seleccionado."
            })

        treatment_list = getattr(estimand, "treatment", ["treatment"])
        instrument_list = getattr(estimand, "instrumental_variables", [["Z"]])

        method_params_dict = {
            "iv.instrumental_variable": {
                "iv_instrument_name": instrument_list[0][0] if instrument_list and instrument_list[0] else "Z"
            },
            "iv.regression_discontinuity": {
                "rd_variable_name": treatment_list[0],
                "rd_threshold_value": 0.5,
                "rd_bandwidth": 0.15,
            },
            "backdoor.propensity_score_weighting": {
                "weighting_scheme": "ips_weight",
            },
            "backdoor.distance_matching": {
                "distance_metric": "minkowski",
                "p": 2,
            },
        }

        method_params = method_params_dict.get(metodo)
        target_units = "att" if metodo == "backdoor.distance_matching" else "ate"

        if method_params:
            estimate = model.estimate_effect(
                estimand,
                method_name=metodo,
                target_units=target_units,
                confidence_intervals=True,
                method_params=method_params,
            )
        else:
            estimate = model.estimate_effect(
                estimand,
                method_name=metodo,
                target_units=target_units,
                confidence_intervals=True,
            )

        st.session_state["estimate"] = estimate

        try:
            intervalo = estimate.get_confidence_intervals()
            if hasattr(intervalo, "tolist"):
                intervalo = intervalo.tolist()
            elif isinstance(intervalo, (list, tuple)):
                intervalo = list(intervalo)
            else:
                intervalo = None
        except Exception:
            intervalo = None

        intervalo_bajo = None
        intervalo_alto = None
        if intervalo and isinstance(intervalo, list):
            first_interval = intervalo[0] if intervalo and isinstance(intervalo[0], list) else intervalo
            if isinstance(first_interval, list) and len(first_interval) >= 2:
                intervalo_bajo = _safe_float(first_interval[0])
                intervalo_alto = _safe_float(first_interval[1])

        estimate_value = _safe_float(estimate.value)
        intervalo_incluye_cero = (
            intervalo_bajo is not None
            and intervalo_alto is not None
            and intervalo_bajo <= 0 <= intervalo_alto
        )

        return json.dumps({
            "estimate": estimate_value,
            "intervalo_confianza": intervalo,
            "intervalo_bajo": intervalo_bajo,
            "intervalo_alto": intervalo_alto,
            "intervalo_incluye_cero": intervalo_incluye_cero,
            "metodo": metodo,
            "target_units": target_units,
        })

    except Exception as e:
        return json.dumps({
            "error": f"Error al estimar el efecto: {str(e)}",
        })


def refute_estimate_tool(input: str = "") -> str:
    try:
        model = st.session_state.get("causal_model")
        estimand = st.session_state.get("identified_estimand")
        estimate = st.session_state.get("estimate")

        if model is None or estimand is None or estimate is None:
            return json.dumps({
                "error": "Faltan el modelo causal, el estimando o el estimate en session_state."
            })

        method = "random_common_cause"
        refutation = model.refute_estimate(
            estimand,
            estimate,
            method_name=method,
        )

        refutation_text = str(refutation)
        p_valor = getattr(refutation, "p_value", None)
        if p_valor is None:
            match = re.search(r"p\s*value\s*:\s*([0-9.eE+-]+)", refutation_text)
            if match:
                p_valor = _safe_float(match.group(1))

        estimate_value = _safe_float(getattr(estimate, "value", None))
        new_effect = _safe_float(getattr(refutation, "new_effect", None))
        cambio_absoluto = None
        cambio_relativo = None
        if estimate_value not in (None, 0) and new_effect is not None:
            cambio_absoluto = new_effect - estimate_value
            cambio_relativo = abs(cambio_absoluto) / abs(estimate_value)

        resultado = {
            "metodo": method,
            "refutacion": refutation_text,
            "p_valor": p_valor,
            "estimate": estimate_value,
            "new_effect": new_effect,
            "cambio_absoluto": cambio_absoluto,
            "cambio_relativo": cambio_relativo,
        }

        return json.dumps({
            "refutaciones": [resultado],
        })

    except Exception as e:
        return json.dumps({
            "error": f"Error al validar el estimado: {str(e)}",
        })


causal_tools = [
    Tool.from_function(
        func=identify_causal_effect,
        name="identify_causal_effect",
        description="Identify causal effect using DoWhy model and return the estimand with backdoor variables.",
    ),
    Tool(
        name="generate_dag",
        func=generate_dag,
        description="Genera un grafico DAG en formato DOT para DoWhy. Recibe un string JSON con: treatment, outcome, correlaciones, confusoras_categoricas.",
    ),
    Tool.from_function(
        func=estimate_causal_effect_tool,
        name="estimate_causal_effect_tool",
        description="Ejecuta la estimacion causal usando el modelo de DoWhy, el estimando identificado y el metodo seleccionado. Devuelve el valor estimado y su intervalo de confianza en JSON.",
    ),
    Tool.from_function(
        func=refute_estimate_tool,
        name="refute_estimate_tool",
        description="Valida la robustez del efecto estimado aplicando el metodo 'random_common_cause' con model.refute_estimate(). Devuelve un JSON con el resultado.",
    ),
]
