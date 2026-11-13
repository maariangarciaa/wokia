import json
import re
from dataclasses import dataclass

import pandas as pd
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.agents.mrkl.output_parser import MRKLOutputParser

from auto_doc.analysis.agent_outputs import parse_treatment_code_response
from auto_doc.analysis.causal import dag_input_summary
from auto_doc.analysis.causal_modeling import build_causal_model_from_dot
from auto_doc.causal.dag import generate_dag
from auto_doc.causal.diagnostics import diagnostico_causal_df
from auto_doc.causal.tools import make_candidate_variables_tool
from auto_doc.causal.workflow import (
    extraer_codigo_tratamiento,
    parse_json_like,
    recomendar_metodo_desde_diagnostico,
)
from auto_doc.models.causal_agent import CausalAgentFactory, CausalLLM
from auto_doc.services.prompts import (
    generar_descripcion_dataset,
    generar_prompt_dag_con_datos,
    generar_prompt_codigo_tratamiento,
    generar_prompt_hipotesis,
    generar_prompt_interpretar_estimacion_causal,
    generar_prompt_validacion_robustez,
)


@dataclass
class CandidateVariablesResult:
    objetivo: str | None
    candidatas: list[str]
    correlaciones: dict[str, float]
    error: str | None = None
    aviso: str | None = None
    columnas_disponibles: list[str] | None = None


@dataclass
class CausalHypothesesResult:
    objetivo: str
    candidata: str
    hipotesis: list[str]


@dataclass
class TreatmentCodeResult:
    hipotesis: str
    explicacion: str
    codigo: str
    applied: bool
    treatment_counts: dict[str, int]
    columns: list[str]
    preview: list[dict]


@dataclass
class CausalDagResult:
    outcome: str
    treatment: str
    dot: str
    source: str
    resumen: dict
    treatment_counts: dict[str, int]


@dataclass
class CausalIdentificationResult:
    outcome: str
    treatment: str
    criterio: str
    backdoor_variables: list[str]
    estimand_text: str
    n_observations: int
    graph_nodes: list[str]
    graph_edges: list[tuple[str, str]]


@dataclass
class EstimationMethodRecommendationResult:
    treatment: str
    backdoor_variables: list[str]
    metodo_recomendado: str
    justificacion: str
    puntos_diagnostico: list[str]
    aspectos_positivos: list[str]
    cautelas: list[str]
    diagnostico: dict
    source: str
    raw_agent_response: str | None = None


@dataclass
class CausalEstimateResult:
    outcome: str
    treatment: str
    metodo: str
    estimate: float | None
    intervalo_confianza: list | None
    intervalo_bajo: float | None
    intervalo_alto: float | None
    intervalo_incluye_cero: bool
    target_units: str
    interpretacion: str
    source: str
    raw_agent_response: str | None
    error: str | None = None


@dataclass
class CausalRefuteResult:
    outcome: str
    treatment: str
    metodo_estimacion: str
    metodo_refutacion: str
    estimate: float | None
    new_effect: float | None
    cambio_absoluto: float | None
    cambio_relativo: float | None
    p_valor: float | None
    refutacion: str
    interpretacion: str
    source: str
    raw_agent_response: str | None
    error: str | None = None


def _clean_hypothesis_lines(text: str) -> list[str]:
    hypotheses = []
    ignored_prefixes = (
        "aqui hay",
        "aquÃ­ hay",
        "estas son",
        "hipotesis",
        "hipÃ³tesis",
    )

    for line in text.splitlines():
        cleaned = line.strip()
        cleaned = cleaned.lstrip("-*• ").strip()
        cleaned = cleaned.removeprefix("1.").removeprefix("2.").removeprefix("3.").strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith(ignored_prefixes):
            continue
        hypotheses.append(cleaned)

    return hypotheses[:3]


def _parse_method_agent_response(text: str) -> dict:
    try:
        return parse_json_like(text)
    except Exception:
        pass

    method_match = re.search(r'"metodo_recomendado"\s*:\s*"([^"]+)"', text)
    if not method_match:
        raise ValueError("No se encontro metodo_recomendado en la respuesta del agente.")

    justification_marker = re.search(r'"justificacion"\s*:\s*"', text)
    if not justification_marker:
        raise ValueError("No se encontro justificacion en la respuesta del agente.")

    start = justification_marker.end()
    end = text.rfind('"')
    if end <= start:
        raise ValueError("No se pudo extraer la justificacion del agente.")

    justification = text[start:end]
    justification = justification.replace('\\"', '"').replace("\\n", "\n")

    return {
        "metodo_recomendado": method_match.group(1),
        "justificacion": justification.strip(),
    }


def find_candidate_variables(df: pd.DataFrame, question: str) -> CandidateVariablesResult:
    tool = make_candidate_variables_tool(df)
    raw_result = tool.run(question)

    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError as exc:
        raise ValueError(f"No se pudo interpretar la respuesta de candidatas como JSON: {raw_result}") from exc

    return CandidateVariablesResult(
        objetivo=parsed.get("objetivo"),
        candidatas=parsed.get("candidatas", []),
        correlaciones=parsed.get("correlaciones", {}),
        error=parsed.get("error"),
        aviso=parsed.get("aviso"),
        columnas_disponibles=parsed.get("columnas_disponibles"),
    )


def generate_causal_hypotheses(
    df: pd.DataFrame,
    objetivo: str,
    candidata: str,
    llm_runner=None,
) -> CausalHypothesesResult:
    if objetivo not in df.columns:
        raise ValueError(f"La variable objetivo no existe en el dataset: {objetivo}")
    if candidata not in df.columns:
        raise ValueError(f"La variable candidata no existe en el dataset: {candidata}")
    if objetivo == candidata:
        raise ValueError("La variable objetivo y la candidata no pueden ser la misma columna.")

    prompt = generar_prompt_hipotesis(
        variable_objetivo=objetivo,
        variable_independiente=candidata,
        df_info=generar_descripcion_dataset(df),
    )
    runner = llm_runner or CausalLLM().run
    raw_response = runner(prompt)
    hypotheses = _clean_hypothesis_lines(raw_response)

    if not hypotheses:
        raise ValueError(f"No se pudieron extraer hipotesis de la respuesta del LLM: {raw_response}")

    return CausalHypothesesResult(
        objetivo=objetivo,
        candidata=candidata,
        hipotesis=hypotheses,
    )


def generate_treatment_code(
    df: pd.DataFrame,
    hipotesis: str,
    agent_runner=None,
    apply_code: bool = True,
) -> TreatmentCodeResult:
    prompt = generar_prompt_codigo_tratamiento(hipotesis)

    if agent_runner is None:
        agent = CausalAgentFactory().create_agent(
            df,
            allowed_tool_names=["python_repl_ast"],
            max_iterations=4,
        )
        raw_response = agent.run(prompt)
    else:
        raw_response = agent_runner(prompt)

    try:
        parsed = parse_treatment_code_response(raw_response)
        explicacion = parsed.explicacion
        codigo = parsed.codigo
    except ValueError:
        fallback = extraer_codigo_tratamiento(raw_response)
        if not fallback:
            raise
        explicacion = fallback["explicacion"]
        codigo = fallback["codigo"]

    if not codigo or "ERROR" in explicacion.upper():
        raise ValueError(explicacion or "No se pudo generar codigo para la columna treatment.")

    treatment_counts: dict[str, int] = {}
    columns = list(df.columns)
    preview: list[dict] = []

    if apply_code:
        namespace = {"df": df.copy()}
        exec(codigo, namespace)
        df_result = namespace["df"]

        if "treatment" not in df_result.columns:
            raise ValueError("El codigo generado no crea la columna treatment.")

        counts = df_result["treatment"].value_counts(dropna=False).to_dict()
        treatment_counts = {str(key): int(value) for key, value in counts.items()}
        columns = list(df_result.columns)
        preview = json.loads(df_result.head(10).to_json(orient="records", date_format="iso"))

    return TreatmentCodeResult(
        hipotesis=hipotesis,
        explicacion=explicacion,
        codigo=codigo,
        applied=apply_code,
        treatment_counts=treatment_counts,
        columns=columns,
        preview=preview,
    )


def apply_treatment_code(df: pd.DataFrame, treatment_code: str | None) -> pd.DataFrame:
    if not treatment_code:
        return df.copy()

    namespace = {"df": df.copy()}
    exec(treatment_code, namespace)
    return namespace["df"]


def generate_causal_dag(
    df: pd.DataFrame,
    outcome: str,
    treatment: str = "treatment",
    treatment_code: str | None = None,
    use_agent: bool = True,
) -> CausalDagResult:
    df_work = apply_treatment_code(df, treatment_code)

    if outcome not in df_work.columns:
        raise ValueError(f"La variable resultado no existe en el dataset: {outcome}")
    if treatment not in df_work.columns:
        raise ValueError(
            f"La columna de tratamiento `{treatment}` no existe. "
            "Envia `treatment_code` o usa una columna de tratamiento ya existente."
        )

    resumen = dag_input_summary(df_work, outcome_col=outcome, treatment_col=treatment)
    fallback_dot = generate_dag(json.dumps(resumen, ensure_ascii=False))
    source = "fallback"
    dot = fallback_dot

    if use_agent:
        prompt = generar_prompt_dag_con_datos(resumen)
        agent = CausalAgentFactory().create_agent(
            df_work,
            allowed_tool_names=["generate_dag"],
            max_iterations=2,
        )
        response = agent.run(prompt)
        match = re.search(r"(digraph\s*\{.*\})", response, re.DOTALL)
        if match:
            dot = match.group(1).strip()
            source = "agent"

    counts = df_work[treatment].value_counts(dropna=False).to_dict()

    return CausalDagResult(
        outcome=outcome,
        treatment=treatment,
        dot=dot,
        source=source,
        resumen=resumen,
        treatment_counts={str(key): int(value) for key, value in counts.items()},
    )


def identify_causal_effect_from_dag(
    df: pd.DataFrame,
    outcome: str,
    dot: str,
    treatment: str = "treatment",
    treatment_code: str | None = None,
) -> CausalIdentificationResult:
    df_work = apply_treatment_code(df, treatment_code)

    if outcome not in df_work.columns:
        raise ValueError(f"La variable resultado no existe en el dataset: {outcome}")
    if treatment not in df_work.columns:
        raise ValueError(
            f"La columna de tratamiento `{treatment}` no existe. "
            "Envia `treatment_code` o usa una columna de tratamiento ya existente."
        )

    build_result = build_causal_model_from_dot(
        df=df_work,
        treatment_col=treatment,
        outcome_col=outcome,
        dot_code=dot,
    )
    estimand = build_result.model.identify_effect()
    backdoors = list(estimand.get_backdoor_variables())
    criterio = "backdoor" if backdoors else "no_identificado"

    return CausalIdentificationResult(
        outcome=outcome,
        treatment=treatment,
        criterio=criterio,
        backdoor_variables=backdoors,
        estimand_text=str(estimand),
        n_observations=int(len(df_work)),
        graph_nodes=list(build_result.graph.nodes()),
        graph_edges=[(str(src), str(dst)) for src, dst in build_result.graph.edges()],
    )


def recommend_estimation_method(
    df: pd.DataFrame,
    treatment: str,
    backdoor_variables: list[str],
    treatment_code: str | None = None,
    use_agent: bool = True,
) -> EstimationMethodRecommendationResult:
    df_work = apply_treatment_code(df, treatment_code)

    if treatment not in df_work.columns:
        raise ValueError(
            f"La columna de tratamiento `{treatment}` no existe. "
            "Envia `treatment_code` o usa una columna de tratamiento ya existente."
        )

    missing_backdoors = [col for col in backdoor_variables if col not in df_work.columns]
    if missing_backdoors:
        raise ValueError(f"Variables de ajuste no encontradas: {missing_backdoors}")
    if not backdoor_variables:
        raise ValueError("No se recibieron variables backdoor para el diagnostico.")

    diagnostico = diagnostico_causal_df(df_work, treatment, backdoor_variables)
    recommendation = recomendar_metodo_desde_diagnostico(diagnostico)
    source = "deterministic"
    raw_agent_response = None

    if use_agent:
        prompt = f"""
Actua como un asistente experto en inferencia causal.

Debes recomendar el metodo de estimacion mas prudente a partir del diagnostico real calculado por el backend.
No ejecutes herramientas, no escribas razonamiento interno y no incluyas bloques de codigo.

Diagnostico:
{json.dumps(diagnostico, ensure_ascii=False)}

Variables backdoor:
{json.dumps(backdoor_variables, ensure_ascii=False)}

Reglas:
- Si hay scores de propension extremos o AUC muy alto, evita matching e IPW puros.
- Si el diagnostico recomienda regresion, devuelve `backdoor.linear_regression`.
- Explica tambien los aspectos positivos que permiten continuar.
- Usa lenguaje claro para personas no expertas.
- Devuelve exclusivamente JSON valido con comillas dobles.
- El JSON debe tener exactamente las claves `metodo_recomendado` y `justificacion`.
- La justificacion debe usar Markdown legible con tres apartados breves: `Resumen`, `Por que encaja` y `Cautela principal`.
"""
        try:
            raw_agent_response = CausalLLM().run(prompt)
            parsed = _parse_method_agent_response(raw_agent_response)
            if parsed.get("metodo_recomendado"):
                recommendation = {
                    "metodo_recomendado": parsed.get("metodo_recomendado"),
                    "justificacion": parsed.get("justificacion", ""),
                    "diagnostico": diagnostico,
                }
                source = "agent"
        except Exception as exc:
            raw_agent_response = raw_agent_response or str(exc)
            source = "deterministic_fallback"

    treatment_info = diagnostico.get("treatment_info", {})
    propensity = diagnostico.get("propensity_score", {})
    backdoor_info = diagnostico.get("backdoor_vars_info", {})

    strong_categoricals = [
        var
        for var, info in backdoor_info.items()
        if info.get("tipo") == "categorica" and info.get("cramers_v", 0) >= 0.7
    ]

    puntos = [
        (
            "Balance de grupos: "
            f"{treatment_info.get('n_tratados', 0)} tratados y "
            f"{treatment_info.get('n_control', 0)} controles "
            f"(proporcion tratados={treatment_info.get('proporcion_tratados')})."
        ),
        (
            "Score de propension: "
            f"AUC={propensity.get('auc')}, "
            f"scores extremos={propensity.get('extremos')}, "
            f"solapamiento={propensity.get('overlap_visual')}."
        ),
        (
            "Variables de ajuste: "
            + (", ".join(backdoor_variables) if backdoor_variables else "ninguna variable de ajuste identificada.")
        ),
    ]

    aspectos_positivos = [
        "El efecto es identificable ajustando por las variables backdoor detectadas.",
        "El flujo puede continuar porque hay observaciones tanto en tratamiento como en control.",
    ]
    if propensity.get("overlap_visual") == "moderado":
        aspectos_positivos.append("El diagnostico detecta un solapamiento moderado entre grupos.")

    cautelas = []
    if propensity.get("extremos"):
        cautelas.append("Hay scores de propension extremos; matching e IPW pueden ser inestables.")
    if propensity.get("auc") is not None and propensity.get("auc") >= 0.9:
        cautelas.append("Un AUC de propension muy alto sugiere separacion entre tratados y controles.")
    if strong_categoricals:
        cautelas.append(
            "Algunas confusoras categoricas estan muy asociadas al tratamiento: "
            + ", ".join(strong_categoricals)
            + "."
        )

    return EstimationMethodRecommendationResult(
        treatment=treatment,
        backdoor_variables=backdoor_variables,
        metodo_recomendado=recommendation["metodo_recomendado"],
        justificacion=recommendation["justificacion"],
        puntos_diagnostico=puntos,
        aspectos_positivos=aspectos_positivos,
        cautelas=cautelas,
        diagnostico=diagnostico,
        source=source,
        raw_agent_response=raw_agent_response,
    )


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _estimate_effect_object(model, estimand, metodo: str):
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

    return estimate, target_units


def _estimate_effect_payload(model, estimand, metodo: str) -> dict:
    estimate, target_units = _estimate_effect_object(model, estimand, metodo)

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

    return {
        "estimate": estimate_value,
        "intervalo_confianza": intervalo,
        "intervalo_bajo": intervalo_bajo,
        "intervalo_alto": intervalo_alto,
        "intervalo_incluye_cero": intervalo_incluye_cero,
        "metodo": metodo,
        "target_units": target_units,
    }


def estimate_causal_effect_from_dag(
    df: pd.DataFrame,
    outcome: str,
    dot: str,
    metodo: str,
    treatment: str = "treatment",
    treatment_code: str | None = None,
    use_agent: bool = True,
) -> CausalEstimateResult:
    df_work = apply_treatment_code(df, treatment_code)

    if outcome not in df_work.columns:
        raise ValueError(f"La variable resultado no existe en el dataset: {outcome}")
    if treatment not in df_work.columns:
        raise ValueError(
            f"La columna de tratamiento `{treatment}` no existe. "
            "Envia `treatment_code` o usa una columna de tratamiento ya existente."
        )

    build_result = build_causal_model_from_dot(
        df=df_work,
        treatment_col=treatment,
        outcome_col=outcome,
        dot_code=dot,
    )
    estimand = build_result.model.identify_effect()
    payload = _estimate_effect_payload(build_result.model, estimand, metodo)

    interpretation = (
        f"Estimacion calculada con {metodo}: efecto={payload['estimate']}, "
        f"intervalo=[{payload['intervalo_bajo']}, {payload['intervalo_alto']}]."
    )
    source = "deterministic"
    raw_agent_response = None

    if use_agent:
        def estimate_tool(_: str = "") -> str:
            return json.dumps(payload, ensure_ascii=False)

        tool = Tool.from_function(
            func=estimate_tool,
            name="estimate_causal_effect_tool",
            description="Estima el efecto causal con DoWhy y devuelve JSON con estimate e intervalo de confianza.",
        )
        prompt = generar_prompt_interpretar_estimacion_causal(treatment, outcome, metodo)
        try:
            agent = initialize_agent(
                tools=[tool],
                llm=CausalLLM().load_llm_chat(),
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=2,
                early_stopping_method="generate",
                agent_kwargs={
                    "output_parser": MRKLOutputParser(),
                },
            )
            raw_agent_response = agent.run(prompt)
            if isinstance(raw_agent_response, str) and raw_agent_response.strip():
                interpretation = raw_agent_response.strip()
                source = "agent"
        except Exception as exc:
            raw_agent_response = str(exc)
            source = "deterministic_fallback"

    return CausalEstimateResult(
        outcome=outcome,
        treatment=treatment,
        metodo=metodo,
        estimate=payload["estimate"],
        intervalo_confianza=payload["intervalo_confianza"],
        intervalo_bajo=payload["intervalo_bajo"],
        intervalo_alto=payload["intervalo_alto"],
        intervalo_incluye_cero=payload["intervalo_incluye_cero"],
        target_units=payload["target_units"],
        interpretacion=interpretation,
        source=source,
        raw_agent_response=raw_agent_response,
    )


def _refute_effect_payload(model, estimand, estimate) -> dict:
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

    return {"refutaciones": [resultado]}


def refute_causal_effect_from_dag(
    df: pd.DataFrame,
    outcome: str,
    dot: str,
    metodo: str,
    treatment: str = "treatment",
    treatment_code: str | None = None,
    use_agent: bool = True,
) -> CausalRefuteResult:
    df_work = apply_treatment_code(df, treatment_code)

    if outcome not in df_work.columns:
        raise ValueError(f"La variable resultado no existe en el dataset: {outcome}")
    if treatment not in df_work.columns:
        raise ValueError(
            f"La columna de tratamiento `{treatment}` no existe. "
            "Envia `treatment_code` o usa una columna de tratamiento ya existente."
        )

    build_result = build_causal_model_from_dot(
        df=df_work,
        treatment_col=treatment,
        outcome_col=outcome,
        dot_code=dot,
    )
    estimand = build_result.model.identify_effect()
    estimate_obj, _ = _estimate_effect_object(build_result.model, estimand, metodo)
    payload = _refute_effect_payload(build_result.model, estimand, estimate_obj)
    first = payload["refutaciones"][0]

    interpretation = (
        f"Refutacion {first['metodo']}: estimate={first['estimate']}, "
        f"new_effect={first['new_effect']}, cambio_relativo={first['cambio_relativo']}, "
        f"p_valor={first['p_valor']}."
    )
    source = "deterministic"
    raw_agent_response = None

    if use_agent:
        def refute_tool(_: str = "") -> str:
            return json.dumps(payload, ensure_ascii=False)

        tool = Tool.from_function(
            func=refute_tool,
            name="refute_estimate_tool",
            description="Valida la robustez del efecto estimado con random_common_cause y devuelve JSON.",
        )
        prompt = generar_prompt_validacion_robustez()
        try:
            agent = initialize_agent(
                tools=[tool],
                llm=CausalLLM().load_llm_chat(),
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=2,
                early_stopping_method="generate",
                agent_kwargs={
                    "output_parser": MRKLOutputParser(),
                },
            )
            raw_agent_response = agent.run(prompt)
            if isinstance(raw_agent_response, str) and raw_agent_response.strip():
                interpretation = raw_agent_response.strip()
                source = "agent"
        except Exception as exc:
            raw_agent_response = str(exc)
            source = "deterministic_fallback"

    return CausalRefuteResult(
        outcome=outcome,
        treatment=treatment,
        metodo_estimacion=metodo,
        metodo_refutacion=first["metodo"],
        estimate=first["estimate"],
        new_effect=first["new_effect"],
        cambio_absoluto=first["cambio_absoluto"],
        cambio_relativo=first["cambio_relativo"],
        p_valor=first["p_valor"],
        refutacion=first["refutacion"],
        interpretacion=interpretation,
        source=source,
        raw_agent_response=raw_agent_response,
    )
