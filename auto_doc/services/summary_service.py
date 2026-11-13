from dataclasses import dataclass

import pandas as pd

from auto_doc.analysis.profile import (
    build_dataset_context,
    summarize_duplicates,
    summarize_missing_values,
)
from auto_doc.models.causal_agent import CausalLLM


SUMMARY_TASKS = {
    "structure",
    "columns",
    "missing",
    "duplicates",
    "correlations",
    "feature_ideas",
    "target",
    "outliers",
}


@dataclass
class AssistantSummaryResult:
    task: str
    answer: str
    mode: str


def build_contextual_summary_prompt(task_prompt: str, dataset_context: str) -> str:
    return f"""
Contexto real del dataset:
{dataset_context}

Instrucciones:
- Responde completamente en espanol.
- Usa solo la informacion del contexto real del dataset.
- No digas que no tienes acceso al dataset.
- No inventes columnas, filas ni valores.
- No incluyas codigo.
- Manten los nombres de columnas exactamente como aparecen.
- No menciones `df`, DataFrame, tabla de nulos ni el proceso interno.
- No uses preambulos como "Sin embargo", "si se requiere", "en resumen" o "propuesta de nuevas variables".
- Responde directamente a la tarea, sin repetir la misma idea dos veces.
- Si no hay hallazgos, dilo en una sola frase breve.
- En sugerencias de nuevas variables, cada propuesta debe incluir:
  - nombre de variable nuevo en formato `snake_case`;
  - formula o regla de calculo usando columnas existentes;
  - utilidad en una frase corta.

Tarea:
{task_prompt}
"""


def get_summary_task_prompt(task: str) -> str:
    prompts = {
        "structure": """
Describe la estructura del dataset: numero de filas, numero de columnas y tipo de variable de cada columna.
Clasifica cada columna como numerica continua/discreta, categorica nominal/ordinal, booleana, fecha/tiempo u otro tipo.
Usa una lista Markdown y nombres de columnas entre comillas invertidas.
""",
        "columns": """
Explica el posible proposito de cada columna de forma clara y accesible.
No inventes significados si el nombre de la columna no es suficiente: indica que requiere validacion de dominio.
Usa una lista Markdown.
""",
        "correlations": """
Analiza las correlaciones numericas disponibles en el contexto.
Indica relaciones fuertes, posibles redundancias y senales utiles para analisis posterior.
Si no hay suficientes columnas numericas, dilo claramente.
""",
        "feature_ideas": """
Propón variables derivadas utiles que puedan calcularse con columnas existentes.
Por cada propuesta incluye:
- **nombre_en_codigo**
- formula o regla de calculo usando columnas existentes
- utilidad concreta para analisis o modelado
No inventes columnas.
""",
        "target": """
Propón una posible variable objetivo para modelado supervisado.
Justifica brevemente por que podria ser adecuada y que tipo de problema permitiria plantear.
Si no hay una candidata clara, dilo y sugiere que haria falta definir el objetivo de negocio.
""",
        "outliers": """
Analiza posibles senales de valores extremos a partir del resumen numerico.
Indica columnas candidatas a revisar y por que.
Si no hay informacion suficiente, dilo de forma breve.
""",
    }
    if task not in SUMMARY_TASKS:
        allowed = ", ".join(sorted(SUMMARY_TASKS))
        raise ValueError(f"Tarea no soportada: {task}. Tareas permitidas: {allowed}")
    if task not in prompts:
        raise ValueError(f"La tarea {task} no usa LLM.")
    return prompts[task]


def assistant_summary(
    df: pd.DataFrame,
    task: str,
    llm_runner: CausalLLM | None = None,
) -> AssistantSummaryResult:
    if task not in SUMMARY_TASKS:
        allowed = ", ".join(sorted(SUMMARY_TASKS))
        raise ValueError(f"Tarea no soportada: {task}. Tareas permitidas: {allowed}")

    if task == "missing":
        return AssistantSummaryResult(task=task, answer=summarize_missing_values(df), mode="deterministic")
    if task == "duplicates":
        return AssistantSummaryResult(task=task, answer=summarize_duplicates(df), mode="deterministic")

    dataset_context = build_dataset_context(df)
    prompt = build_contextual_summary_prompt(get_summary_task_prompt(task), dataset_context)
    llm_runner = llm_runner or CausalLLM()
    answer = llm_runner.run(prompt)
    return AssistantSummaryResult(task=task, answer=answer, mode="llm")
