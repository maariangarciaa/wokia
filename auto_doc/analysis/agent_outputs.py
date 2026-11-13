import json
import re
from dataclasses import dataclass


@dataclass
class TreatmentCodeResponse:
    json_text: str
    explicacion: str
    codigo: str


def extract_json_text(text: str) -> str:
    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)

    object_match = re.search(r"(\{.*?\})", text, re.DOTALL)
    if object_match:
        return object_match.group(1)

    raise ValueError("No se encontro JSON valido en la respuesta del agente.")


def parse_treatment_code_response(text: str) -> TreatmentCodeResponse:
    json_text = extract_json_text(text)
    parsed = json.loads(json_text)

    return TreatmentCodeResponse(
        json_text=json_text,
        explicacion=parsed.get("explicacion", ""),
        codigo=parsed.get("codigo", "").strip(),
    )
