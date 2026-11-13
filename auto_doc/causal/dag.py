import json
import re


def generate_dag(resumen_str: str) -> str:
    resumen_str = resumen_str.strip()
    fenced = re.search(r"```(?:json|python)?\s*(.*?)\s*```", resumen_str, re.DOTALL)
    if fenced:
        resumen_str = fenced.group(1).strip()

    json_match = re.search(r"\{.*\}", resumen_str, re.DOTALL)
    if json_match:
        resumen_str = json_match.group(0).strip()

    if resumen_str.startswith("```json"):
        resumen_str = resumen_str[len("```json"):].strip()
    if resumen_str.startswith("```python"):
        resumen_str = resumen_str[len("```python"):].strip()
    if resumen_str.endswith("```"):
        resumen_str = resumen_str[:-3].strip()
    if not resumen_str.startswith("{") or not resumen_str.endswith("}"):
        raise ValueError(f"JSON invalido recibido en generar_dag:\n\n{resumen_str}")

    resumen = json.loads(resumen_str)
    treatment = resumen["treatment"]
    outcome = resumen["outcome"]
    corr = {
        key: value
        for key, value in resumen.get("correlaciones", {}).items()
        if key not in {treatment, outcome}
    }
    conf_cat = {
        key: value
        for key, value in resumen.get("confusoras_categoricas", {}).items()
        if key not in {treatment, outcome}
    }

    def quote(var):
        return f'"{var}"'

    dot = [
        "digraph {",
        "node [shape=ellipse, style=filled, fontcolor=black];",
        f'{quote(treatment)} [fillcolor="#B7F7B1", color="#2E7D32", penwidth=2];',
        f'{quote(outcome)} [fillcolor="#D9D9D9", color="#666666", penwidth=2];',
    ]
    for c in conf_cat:
        dot.append(f'{quote(c)} [fillcolor="#FFA500", color="#A65F00"];')
    for m in corr:
        dot.append(f'{quote(m)} [fillcolor="#B7E3EF", color="#4F94A8"];')

    dot.append(f'{quote(treatment)} -> {quote(outcome)};')
    for c in conf_cat:
        dot.append(f'{quote(c)} -> {quote(treatment)};')
        dot.append(f'{quote(c)} -> {quote(outcome)};')
    for m in corr:
        dot.append(f'{quote(treatment)} -> {quote(m)};')
        dot.append(f'{quote(m)} -> {quote(outcome)};')
    dot.append("}")
    return "\n".join(dot)

