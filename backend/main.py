import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from auto_doc.analysis.profile import build_dataset_context, dataset_profile
from auto_doc.analysis.causal_workflow import create_manual_treatment, prepare_outcome
from auto_doc.services.datasets import (
    DATASETS_DIR,
    dataset_metadata,
    dataset_path,
    list_datasets,
    load_dataset,
    normalize_dataset_name,
    save_dataset_bytes,
)
from auto_doc.services.chart_service import generate_and_render_chart, generate_chart_code
from auto_doc.services.causal_service import (
    find_candidate_variables,
    generate_causal_hypotheses,
    generate_causal_dag,
    generate_treatment_code,
    identify_causal_effect_from_dag,
    recommend_estimation_method,
    estimate_causal_effect_from_dag,
    refute_causal_effect_from_dag,
)
from auto_doc.services.summary_service import assistant_summary


app = FastAPI(
    title="Wokia API",
    description="Backend determinista para datasets, perfilado y futura integracion React.",
    version="0.1.0",
)


class AssistantSummaryRequest(BaseModel):
    task: str


class ChartCodeRequest(BaseModel):
    question: str
    prefer_fallback: bool = False


class CausalCandidatesRequest(BaseModel):
    question: str


class CausalHypothesesRequest(BaseModel):
    objetivo: str
    candidata: str


class CausalTreatmentRequest(BaseModel):
    hipotesis: str
    apply_code: bool = True


class CausalManualSetupRequest(BaseModel):
    treatment_source: str
    outcome: str


class CausalDagRequest(BaseModel):
    outcome: str
    treatment: str = "treatment"
    treatment_code: str | None = None
    use_agent: bool = True


class CausalIdentifyRequest(BaseModel):
    outcome: str
    dot: str
    treatment: str = "treatment"
    treatment_code: str | None = None


class CausalMethodRequest(BaseModel):
    treatment: str = "treatment"
    backdoor_variables: list[str]
    treatment_code: str | None = None
    use_agent: bool = True


class CausalEstimateRequest(BaseModel):
    outcome: str
    dot: str
    metodo: str
    treatment: str = "treatment"
    treatment_code: str | None = None
    use_agent: bool = True


class CausalRefuteRequest(BaseModel):
    outcome: str
    dot: str
    metodo: str
    treatment: str = "treatment"
    treatment_code: str | None = None
    use_agent: bool = True


def resolve_existing_dataset(file_name: str) -> Path:
    safe_name = normalize_dataset_name(file_name)
    path = dataset_path(safe_name)
    base_dir = DATASETS_DIR.resolve()
    resolved = path.resolve()

    if base_dir not in resolved.parents and resolved != base_dir:
        raise HTTPException(status_code=400, detail="Nombre de archivo no valido.")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Dataset no encontrado: {safe_name}")
    return resolved


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "wokia-api"}


@app.get("/datasets")
def get_datasets() -> dict[str, list[dict[str, str]]]:
    return {"datasets": list_datasets()}


@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    file_name = normalize_dataset_name(file.filename or "")
    if not file_name:
        raise HTTPException(status_code=400, detail="Nombre de archivo no valido.")

    try:
        content = await file.read()
        if not content:
            raise ValueError("El archivo esta vacio.")
        path = save_dataset_bytes(file_name, content)
        df = load_dataset(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        saved_path = dataset_path(file_name)
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=400, detail=f"No se pudo leer el dataset: {exc}") from exc

    return {
        "file_name": path.name,
        "metadata": dataset_metadata(df, path.name),
    }


@app.get("/datasets/{file_name}/metadata")
def get_dataset_metadata(file_name: str) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return dataset_metadata(df, path.name)


@app.get("/datasets/{file_name}/profile")
def get_dataset_profile(file_name: str) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return dataset_profile(df, path.name)


@app.get("/datasets/{file_name}/profile-context")
def get_dataset_profile_context(file_name: str) -> dict[str, str]:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "file_name": path.name,
        "profile_context": build_dataset_context(df),
    }


@app.post("/datasets/{file_name}/assistant-summary")
def post_dataset_assistant_summary(file_name: str, request: AssistantSummaryRequest) -> dict[str, str]:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = assistant_summary(df, request.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "task": result.task,
        "mode": result.mode,
        "answer": result.answer,
    }


@app.post("/datasets/{file_name}/charts/code")
def post_dataset_chart_code(file_name: str, request: ChartCodeRequest) -> dict[str, str | bool | None]:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = generate_chart_code(
            df=df,
            question=request.question,
            prefer_fallback=request.prefer_fallback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "question": request.question,
        "source": result.source,
        "fallback_used": result.source == "fallback",
        "code": result.code,
    }


@app.post("/datasets/{file_name}/charts/render")
def post_dataset_chart_render(file_name: str, request: ChartCodeRequest) -> dict[str, str | bool]:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = generate_and_render_chart(
            df=df,
            question=request.question,
            prefer_fallback=request.prefer_fallback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "question": request.question,
        "source": result.source,
        "fallback_used": result.source == "fallback",
        "mime_type": result.mime_type,
        "image_base64": result.image_base64,
        "code": result.code,
    }


@app.post("/datasets/{file_name}/causal/candidates")
def post_dataset_causal_candidates(file_name: str, request: CausalCandidatesRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = find_candidate_variables(df, request.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = {
        "file_name": path.name,
        "question": request.question,
        "objetivo": result.objetivo,
        "candidatas": result.candidatas,
        "correlaciones": result.correlaciones,
    }
    if result.aviso:
        response["aviso"] = result.aviso
    if result.error:
        response["error"] = result.error
    if result.columnas_disponibles:
        response["columnas_disponibles"] = result.columnas_disponibles
    return response


@app.post("/datasets/{file_name}/causal/hypotheses")
def post_dataset_causal_hypotheses(file_name: str, request: CausalHypothesesRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = generate_causal_hypotheses(
            df=df,
            objetivo=request.objetivo,
            candidata=request.candidata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "objetivo": result.objetivo,
        "candidata": result.candidata,
        "hipotesis": result.hipotesis,
    }


@app.post("/datasets/{file_name}/causal/treatment")
def post_dataset_causal_treatment(file_name: str, request: CausalTreatmentRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = generate_treatment_code(
            df=df,
            hipotesis=request.hipotesis,
            apply_code=request.apply_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "hipotesis": result.hipotesis,
        "explicacion": result.explicacion,
        "codigo": result.codigo,
        "applied": result.applied,
        "treatment_counts": result.treatment_counts,
        "columns": result.columns,
        "preview": result.preview,
    }


def _py_literal(value) -> str:
    return repr(value.item() if hasattr(value, "item") else value)


@app.post("/datasets/{file_name}/causal/manual-setup")
def post_dataset_causal_manual_setup(file_name: str, request: CausalManualSetupRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        if request.treatment_source not in df.columns:
            raise ValueError(f"La columna de tratamiento no existe: {request.treatment_source}")
        if request.outcome not in df.columns:
            raise ValueError(f"La variable resultado no existe: {request.outcome}")
        if request.treatment_source == request.outcome:
            raise ValueError("La columna de tratamiento y la variable resultado no pueden ser la misma.")

        treatment_result = create_manual_treatment(df, request.treatment_source)
        outcome_result = prepare_outcome(df, treatment_result.df_tratado, request.outcome)
        if not outcome_result.is_valid:
            raise ValueError("La variable resultado debe ser numerica o binaria.")

        code_lines = [
            f'df["treatment"] = (df[{_py_literal(request.treatment_source)}] == {_py_literal(treatment_result.value_1)}).astype(int)'
        ]
        if outcome_result.was_converted:
            code_lines.append(
                f'df[{_py_literal(request.outcome)}] = (df[{_py_literal(request.outcome)}] == {_py_literal(outcome_result.value_1)}).astype(int)'
            )
        setup_code = "\n".join(code_lines)
        counts = outcome_result.df_tratado["treatment"].value_counts(dropna=False).to_dict()
        preview = json.loads(outcome_result.df_tratado.head(10).to_json(orient="records", date_format="iso"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "treatment": "treatment",
        "treatment_source": request.treatment_source,
        "outcome": request.outcome,
        "setup_code": setup_code,
        "treatment_counts": {str(key): int(value) for key, value in counts.items()},
        "treatment_was_binary": treatment_result.was_binary,
        "treatment_value_1": str(treatment_result.value_1),
        "treatment_value_0": str(treatment_result.value_0),
        "outcome_was_converted": outcome_result.was_converted,
        "outcome_value_1": None if outcome_result.value_1 is None else str(outcome_result.value_1),
        "outcome_value_0": None if outcome_result.value_0 is None else str(outcome_result.value_0),
        "preview": preview,
    }


@app.post("/datasets/{file_name}/causal/dag")
def post_dataset_causal_dag(file_name: str, request: CausalDagRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = generate_causal_dag(
            df=df,
            outcome=request.outcome,
            treatment=request.treatment,
            treatment_code=request.treatment_code,
            use_agent=request.use_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "outcome": result.outcome,
        "treatment": result.treatment,
        "source": result.source,
        "dot": result.dot,
        "resumen": result.resumen,
        "treatment_counts": result.treatment_counts,
    }


@app.post("/datasets/{file_name}/causal/identify")
def post_dataset_causal_identify(file_name: str, request: CausalIdentifyRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = identify_causal_effect_from_dag(
            df=df,
            outcome=request.outcome,
            dot=request.dot,
            treatment=request.treatment,
            treatment_code=request.treatment_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "outcome": result.outcome,
        "treatment": result.treatment,
        "criterio": result.criterio,
        "backdoor_variables": result.backdoor_variables,
        "estimand_text": result.estimand_text,
        "n_observations": result.n_observations,
        "graph_nodes": result.graph_nodes,
        "graph_edges": result.graph_edges,
    }


@app.post("/datasets/{file_name}/causal/method")
def post_dataset_causal_method(file_name: str, request: CausalMethodRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = recommend_estimation_method(
            df=df,
            treatment=request.treatment,
            backdoor_variables=request.backdoor_variables,
            treatment_code=request.treatment_code,
            use_agent=request.use_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "treatment": result.treatment,
        "backdoor_variables": result.backdoor_variables,
        "metodo_recomendado": result.metodo_recomendado,
        "justificacion": result.justificacion,
        "source": result.source,
        "puntos_diagnostico": result.puntos_diagnostico,
        "aspectos_positivos": result.aspectos_positivos,
        "cautelas": result.cautelas,
        "diagnostico": result.diagnostico,
        "raw_agent_response": result.raw_agent_response,
    }


@app.post("/datasets/{file_name}/causal/estimate")
def post_dataset_causal_estimate(file_name: str, request: CausalEstimateRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = estimate_causal_effect_from_dag(
            df=df,
            outcome=request.outcome,
            dot=request.dot,
            metodo=request.metodo,
            treatment=request.treatment,
            treatment_code=request.treatment_code,
            use_agent=request.use_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "outcome": result.outcome,
        "treatment": result.treatment,
        "metodo": result.metodo,
        "estimate": result.estimate,
        "intervalo_confianza": result.intervalo_confianza,
        "intervalo_bajo": result.intervalo_bajo,
        "intervalo_alto": result.intervalo_alto,
        "intervalo_incluye_cero": result.intervalo_incluye_cero,
        "target_units": result.target_units,
        "interpretacion": result.interpretacion,
        "source": result.source,
        "raw_agent_response": result.raw_agent_response,
        "error": result.error,
    }


@app.post("/datasets/{file_name}/causal/refute")
def post_dataset_causal_refute(file_name: str, request: CausalRefuteRequest) -> dict:
    path = resolve_existing_dataset(file_name)
    try:
        df = load_dataset(path)
        result = refute_causal_effect_from_dag(
            df=df,
            outcome=request.outcome,
            dot=request.dot,
            metodo=request.metodo,
            treatment=request.treatment,
            treatment_code=request.treatment_code,
            use_agent=request.use_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "file_name": path.name,
        "outcome": result.outcome,
        "treatment": result.treatment,
        "metodo_estimacion": result.metodo_estimacion,
        "metodo_refutacion": result.metodo_refutacion,
        "estimate": result.estimate,
        "new_effect": result.new_effect,
        "cambio_absoluto": result.cambio_absoluto,
        "cambio_relativo": result.cambio_relativo,
        "p_valor": result.p_valor,
        "refutacion": result.refutacion,
        "interpretacion": result.interpretacion,
        "source": result.source,
        "raw_agent_response": result.raw_agent_response,
        "error": result.error,
    }
