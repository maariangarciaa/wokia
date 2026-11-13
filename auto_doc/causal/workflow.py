import ast
import json
import re


def parse_json_like(texto: str):
    match = re.search(r"\{.*\}", str(texto), re.DOTALL)
    if not match:
        raise ValueError("No se encontro un objeto JSON en la respuesta.")

    json_text = match.group(0)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return ast.literal_eval(json_text)


def extraer_codigo_tratamiento(respuesta: str):
    bloques = re.findall(r"```(?:python)?\s*(.*?)```", str(respuesta), re.DOTALL)
    candidatos = bloques or re.findall(r"Action Input:\s*(.*?)(?:\nObservation:|\nThought:|\Z)", str(respuesta), re.DOTALL)

    for codigo in reversed(candidatos):
        codigo = codigo.strip()
        if 'df["treatment"]' not in codigo and "df['treatment']" not in codigo:
            continue

        lineas_limpias = []
        for linea in codigo.splitlines():
            stripped = linea.strip()
            if not stripped or stripped.startswith("print("):
                continue
            lineas_limpias.append(linea)

        codigo_limpio = "\n".join(lineas_limpias).strip()
        if codigo_limpio:
            return {
                "explicacion": "La columna `treatment` se genera aplicando la regla binaria propuesta en la hipotesis causal.",
                "codigo": codigo_limpio,
            }

    return None


def recomendar_metodo_desde_diagnostico(diagnostico: dict):
    treatment_info = diagnostico.get("treatment_info", {})
    propensity = diagnostico.get("propensity_score", {})
    recomendaciones = diagnostico.get("recomendaciones_metodologicas", {})
    backdoor_info = diagnostico.get("backdoor_vars_info", {})

    n_tratados = treatment_info.get("n_tratados", 0)
    n_control = treatment_info.get("n_control", 0)
    proporcion_tratados = treatment_info.get("proporcion_tratados", 0)
    auc = propensity.get("auc")
    extremos = bool(propensity.get("extremos", False))
    overlap = propensity.get("overlap_visual", "no evaluado")

    asociaciones_altas = [
        var
        for var, info in backdoor_info.items()
        if info.get("tipo") == "categorica" and info.get("cramers_v", 0) >= 0.7
    ]

    grupos_desbalanceados = (
        n_tratados == 0
        or n_control == 0
        or proporcion_tratados < 0.25
        or proporcion_tratados > 0.75
    )

    if recomendaciones.get("usar_regresion") and (
        extremos or grupos_desbalanceados or (auc is not None and auc >= 0.9)
    ):
        metodo = "backdoor.linear_regression"
        motivo = (
            "Se recomienda regresion porque el diagnostico detecta un escenario poco adecuado para metodos basados "
            "en propensity score puros: hay scores extremos o separacion alta entre tratados y controles."
        )
    elif recomendaciones.get("usar_matching"):
        metodo = "backdoor.propensity_score_matching"
        motivo = (
            "Se recomienda matching porque el solapamiento entre tratados y controles parece suficiente y no se "
            "detectan scores de propension extremos."
        )
    elif recomendaciones.get("usar_ipw"):
        metodo = "backdoor.propensity_score_weighting"
        motivo = (
            "Se recomienda ponderacion por propensity score porque el diagnostico no detecta scores extremos y el "
            "solapamiento es razonable."
        )
    else:
        metodo = "backdoor.linear_regression"
        motivo = (
            "Se usa regresion como opcion conservadora porque el diagnostico no apoya claramente matching ni "
            "ponderacion."
        )

    detalles = [
        f"tratados={n_tratados}",
        f"control={n_control}",
        f"proporcion_tratados={proporcion_tratados}",
        f"AUC_propension={auc}",
        f"scores_extremos={extremos}",
        f"solapamiento={overlap}",
    ]
    if asociaciones_altas:
        detalles.append("confusoras_categoricas_fuertes=" + ", ".join(asociaciones_altas))

    return {
        "metodo_recomendado": metodo,
        "justificacion": f"{motivo} Diagnostico: {', '.join(detalles)}.",
        "diagnostico": diagnostico,
    }
