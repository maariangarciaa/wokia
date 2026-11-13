import base64
import io
import re
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from auto_doc.analysis.charts import (
    build_chart_fallback,
    build_graph_context,
    sanitize_generated_code,
)
from auto_doc.models.causal_agent import CausalLLM


@dataclass
class ChartCodeResult:
    code: str
    source: str
    raw_response: str | None = None


@dataclass
class ChartRenderResult:
    code: str
    source: str
    image_base64: str
    mime_type: str = "image/png"


def build_chart_prompt(df: pd.DataFrame, question: str) -> str:
    instructions = """
Eres un analista de datos experto en visualizacion, especializado exclusivamente en generar codigo Python para construir graficos con matplotlib o seaborn.

Si la solicitud no esta relacionada con crear un grafico, responde:
"No estoy especializado para eso, pide otra cosa."

Si la solicitud no esta claramente relacionada con un grafico especifico o es ambigua, responde:
"No puedo generar un grafico con esa peticion. Por favor, se claro y especifico indicando que columnas o tipo de grafico deseas."

Tu entorno ya tiene un DataFrame precargado llamado `df`. Tu unica tarea es devolver el codigo necesario para construir la visualizacion que se te pide:

1. Usa `matplotlib` o `seaborn`.
2. No llames a `st.pyplot()` ni a `plt.show()`.
3. No imprimas ni devuelvas resultados de funciones como `plt.title()`, `plt.xlabel()`, etc.; asigna a `_` si hace falta.
4. Usa el color por defecto `'#A4C6E8'`, salvo que el usuario pida otro color.
5. Si generas un pie chart, usa `wedgeprops={'edgecolor': 'black', 'linewidth': 1}`.
6. El codigo debe estar en ingles y ser Python valido.
7. Devuelve solo un bloque ```python ... ```.
"""
    return (
        instructions
        + "\n\nContexto real del dataset:\n"
        + build_graph_context(df)
        + "\n\nReglas adicionales: no uses herramientas, no ejecutes codigo, no expliques nada y devuelve solo un bloque ```python ... ``` usando columnas existentes. Para graficos de correlacion, usa solo columnas numericas con df.select_dtypes(include='number') o una lista explicita de columnas numericas.\n"
        + "\n\nSolicitud del usuario:\n"
        + question
    )


def extract_python_code(text: str) -> str:
    normalized = text.replace("````", "```")
    match = re.search(r"```(?:python)?\s*(.*?)```", normalized, re.DOTALL)
    if not match:
        raise ValueError("No se genero ningun bloque de codigo Python valido.")
    return match.group(1).strip()


def generate_chart_code(
    df: pd.DataFrame,
    question: str,
    llm_runner: CausalLLM | None = None,
    prefer_fallback: bool = False,
) -> ChartCodeResult:
    fallback = build_chart_fallback(question, df)
    if prefer_fallback:
        if not fallback:
            raise ValueError("No hay fallback determinista para esta peticion.")
        code = extract_python_code(fallback)
        return ChartCodeResult(code=code, source="fallback", raw_response=fallback)

    llm_runner = llm_runner or CausalLLM()
    raw_response = llm_runner.run(build_chart_prompt(df, question))
    code = sanitize_generated_code(extract_python_code(raw_response), question)
    return ChartCodeResult(code=code, source="llm", raw_response=raw_response)


def render_chart_code(df: pd.DataFrame, code: str) -> str:
    plt.close("all")
    local_scope = {"df": df, "plt": plt, "sns": sns}
    exec(code, {}, local_scope)

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("ascii")
    plt.close("all")
    return image_base64


def generate_and_render_chart(
    df: pd.DataFrame,
    question: str,
    llm_runner: CausalLLM | None = None,
    prefer_fallback: bool = False,
) -> ChartRenderResult:
    code_result = generate_chart_code(
        df=df,
        question=question,
        llm_runner=llm_runner,
        prefer_fallback=prefer_fallback,
    )
    image_base64 = render_chart_code(df, code_result.code)
    return ChartRenderResult(
        code=code_result.code,
        source=code_result.source,
        image_base64=image_base64,
    )
