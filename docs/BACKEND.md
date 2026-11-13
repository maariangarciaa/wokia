# Backend FastAPI

La API FastAPI proporciona las operaciones utilizadas por la interfaz React, incluidas llamadas al LLM y al agente donde corresponde. Streamlit se conserva como version anterior.

## Ejecutar backend

Activa el entorno virtual:

```powershell
.\venv\Scripts\Activate.ps1
```

Lanza la API:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Abre la documentacion interactiva:

```text
http://localhost:8000/docs
```

## Flujo causal completo

El flujo causal principal de la API sigue este orden:

```text
candidates -> hypotheses -> treatment -> dag -> identify -> method -> estimate -> refute
```

Para probarlo en Postman con `ElectricCarData_Clean.csv`, puedes usar los cuerpos JSON guardados en:

```text
docs/api_examples/
```

Orden de endpoints:

| Paso | Endpoint | Ejemplo |
| --- | --- | --- |
| 1 | `POST /datasets/{file_name}/causal/candidates` | `docs/api_examples/01_causal_candidates.json` |
| 2 | `POST /datasets/{file_name}/causal/hypotheses` | `docs/api_examples/02_causal_hypotheses.json` |
| 3 | `POST /datasets/{file_name}/causal/treatment` | `docs/api_examples/03_causal_treatment.json` |
| 4 | `POST /datasets/{file_name}/causal/dag` | `docs/api_examples/04_causal_dag.json` |
| 5 | `POST /datasets/{file_name}/causal/identify` | `docs/api_examples/05_causal_identify.json` |
| 6 | `POST /datasets/{file_name}/causal/method` | `docs/api_examples/06_causal_method.json` |
| 7 | `POST /datasets/{file_name}/causal/estimate` | `docs/api_examples/07_causal_estimate.json` |
| 8 | `POST /datasets/{file_name}/causal/refute` | `docs/api_examples/08_causal_refute.json` |

Notas del flujo:

- Los endpoints `hypotheses`, `treatment`, `dag`, `method`, `estimate` y `refute` usan LLM/agente por defecto cuando aplica.
- Los endpoints `candidates` e `identify` son deterministas porque resuelven calculos formales.
- Para pruebas sin gastar tokens, los endpoints con `use_agent` aceptan `false`.
- Los ejemplos 5, 7 y 8 incluyen un DAG completo ya generado para que puedas probarlos sin copiar el DOT manualmente.

## Endpoints actuales

### Health check

```http
GET /health
```

Devuelve el estado basico de la API.

### Listar datasets

```http
GET /datasets
```

Lista los archivos CSV/XLSX disponibles en `auto_doc/files`.

### Metadata de dataset

```http
GET /datasets/{file_name}/metadata
```

Carga el dataset y devuelve informacion estructural:

- filas;
- columnas;
- nombres de columnas;
- columnas numericas;
- columnas categoricas;
- total de nulos;
- duplicados exactos.

### Contexto de perfilado

### Perfil estructurado

```http
GET /datasets/{file_name}/profile
```

Devuelve un perfil determinista en JSON:

- shape del dataset;
- resumen por columna;
- nulos y duplicados;
- columnas numericas y categoricas;
- resumen numerico;
- correlaciones numericas;
- primeras filas para previsualizacion.

Este endpoint esta pensado para el futuro frontend React.

### Contexto de perfilado

```http
GET /datasets/{file_name}/profile-context
```

Devuelve el contexto textual que usa Wokia para el perfilado asistido.

### Resumen asistido

```http
POST /datasets/{file_name}/assistant-summary
```

Body:

```json
{
  "task": "missing"
}
```

Tareas disponibles:

- `structure`: resumen de estructura y tipos de variables usando LLM.
- `columns`: explicacion de columnas usando LLM.
- `missing`: resumen determinista de valores nulos, sin LLM.
- `duplicates`: resumen determinista de duplicados, sin LLM.
- `correlations`: analisis de correlaciones usando LLM.
- `feature_ideas`: sugerencias de variables derivadas usando LLM.
- `target`: posible variable objetivo usando LLM.
- `outliers`: revision de posibles outliers usando LLM.

Respuesta:

```json
{
  "file_name": "dataset.csv",
  "task": "missing",
  "mode": "deterministic",
  "answer": "..."
}
```

### Codigo de graficos

```http
POST /datasets/{file_name}/charts/code
```

Body:

```json
{
  "question": "Haz un boxplot rosa del precio por carroceria",
  "prefer_fallback": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "question": "Haz un boxplot rosa del precio por carroceria",
  "source": "fallback",
  "fallback_used": true,
  "code": "fig, ax = plt.subplots(...)"
}
```

Notas:

- `prefer_fallback: true` no usa LLM; solo funciona para peticiones cubiertas por fallback determinista.
- `prefer_fallback: false` usa el LLM para generar codigo de grafico.
- El endpoint devuelve codigo, no renderiza la imagen todavia.

### Render de graficos

```http
POST /datasets/{file_name}/charts/render
```

Body:

```json
{
  "question": "Haz un boxplot rosa del precio por carroceria",
  "prefer_fallback": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "question": "Haz un boxplot rosa del precio por carroceria",
  "source": "fallback",
  "fallback_used": true,
  "mime_type": "image/png",
  "image_base64": "...",
  "code": "fig, ax = plt.subplots(...)"
}
```

Para visualizar la imagen en un frontend:

```html
<img src="data:image/png;base64,VALOR_DE_image_base64" />
```

### Candidatas causales

```http
POST /datasets/{file_name}/causal/candidates
```

Body:

```json
{
  "question": "que variables influyen en PriceEuro"
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "question": "que variables influyen en PriceEuro",
  "objetivo": "PriceEuro",
  "candidatas": ["TopSpeed_KmH"],
  "correlaciones": {
    "TopSpeed_KmH": 0.8291,
    "Range_Km": 0.6748,
    "AccelSec": -0.6272
  }
}
```

Este endpoint reutiliza la misma herramienta de candidatas que usa Streamlit en el flujo causal.

### Hipotesis causales

```http
POST /datasets/{file_name}/causal/hypotheses
```

Body:

```json
{
  "objetivo": "PriceEuro",
  "candidata": "TopSpeed_KmH"
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "objetivo": "PriceEuro",
  "candidata": "TopSpeed_KmH",
  "hipotesis": [
    "Los vehiculos cuya velocidad maxima supera los 200 km/h (`TopSpeed_KmH`) tienden a tener precios mas altos (`PriceEuro`).",
    "Los vehiculos con una velocidad maxima superior a 180 km/h (`TopSpeed_KmH`) presentan un precio mayor (`PriceEuro`) que el resto."
  ]
}
```

Este endpoint usa LLM para redactar hipotesis claras a partir de una variable candidata ya seleccionada.

### Generar treatment

```http
POST /datasets/{file_name}/causal/treatment
```

Body:

```json
{
  "hipotesis": "Los vehiculos cuya velocidad maxima supera los 200 km/h (`TopSpeed_KmH`) tienden a tener precios mas altos (`PriceEuro`).",
  "apply_code": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "hipotesis": "...",
  "explicacion": "La columna `treatment` se crea...",
  "codigo": "df[\"treatment\"] = (df[\"TopSpeed_KmH\"] > 200).astype(int)\ndf = df.drop(columns=[\"TopSpeed_KmH\"])",
  "applied": true,
  "treatment_counts": {
    "0": 82,
    "1": 21
  },
  "columns": ["Brand", "Model", "...", "treatment"]
}
```

Este endpoint usa el agente ReAct con `python_repl_ast` para inspeccionar el dataset y generar el codigo de tratamiento. El codigo se valida sobre una copia del dataset; no modifica el archivo original.

### Generar DAG causal

```http
POST /datasets/{file_name}/causal/dag
```

Body:

```json
{
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "treatment_code": "df[\"treatment\"] = (df[\"TopSpeed_KmH\"] > 200).astype(int)\ndf = df.drop(columns=[\"TopSpeed_KmH\"])",
  "use_agent": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "source": "agent",
  "dot": "digraph { ... }",
  "resumen": {
    "treatment": "treatment",
    "outcome": "PriceEuro",
    "correlaciones": {},
    "confusoras_categoricas": {}
  },
  "treatment_counts": {
    "0": 82,
    "1": 21
  }
}
```

Notas:

- `treatment_code` viene del endpoint `/causal/treatment`.
- Si el dataset ya contiene una columna de tratamiento, `treatment_code` puede omitirse.
- `use_agent: true` mantiene el flujo agéntico y llama a la herramienta `generate_dag`.
- `use_agent: false` genera el DOT directamente con la misma herramienta, util para pruebas sin gastar tokens.

### Identificar efecto causal

```http
POST /datasets/{file_name}/causal/identify
```

Body:

```json
{
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "treatment_code": "df[\"treatment\"] = (df[\"TopSpeed_KmH\"] > 200).astype(int)\ndf = df.drop(columns=[\"TopSpeed_KmH\"])",
  "dot": "digraph { ... }"
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "criterio": "backdoor",
  "backdoor_variables": ["Brand", "FastCharge_KmH", "PowerTrain"],
  "estimand_text": "Estimand type: ...",
  "n_observations": 103,
  "graph_nodes": ["treatment", "PriceEuro"],
  "graph_edges": [["treatment", "PriceEuro"]]
}
```

Este endpoint no usa LLM: DoWhy identifica el estimando causal directamente a partir del DAG confirmado.

### Recomendar metodo de estimacion

```http
POST /datasets/{file_name}/causal/method
```

Body:

```json
{
  "treatment": "treatment",
  "treatment_code": "df[\"treatment\"] = (df[\"TopSpeed_KmH\"] > 200).astype(int)\ndf = df.drop(columns=[\"TopSpeed_KmH\"])",
  "backdoor_variables": ["Brand", "BodyStyle", "FastCharge_KmH", "PowerTrain", "Segment"],
  "use_agent": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "treatment": "treatment",
  "backdoor_variables": ["Brand", "BodyStyle", "FastCharge_KmH", "PowerTrain", "Segment"],
  "metodo_recomendado": "backdoor.linear_regression",
  "justificacion": "...",
  "source": "agent",
  "puntos_diagnostico": ["Balance de grupos: ..."],
  "aspectos_positivos": ["..."],
  "cautelas": ["..."],
  "diagnostico": {},
  "raw_agent_response": "..."
}
```

Este endpoint calcula el diagnostico en el backend y, por defecto, llama al LLM para interpretar los datos y recomendar el metodo. Para pruebas sin gastar tokens, envia `"use_agent": false`; en ese caso se usa la recomendacion determinista.

### Estimar efecto causal

```http
POST /datasets/{file_name}/causal/estimate
```

Body:

```json
{
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "treatment_code": "df[\"treatment\"] = (df[\"TopSpeed_KmH\"] > 200).astype(int)\ndf = df.drop(columns=[\"TopSpeed_KmH\"])",
  "dot": "digraph { ... }",
  "metodo": "backdoor.linear_regression",
  "use_agent": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "metodo": "backdoor.linear_regression",
  "estimate": 20075.6,
  "intervalo_bajo": 9356.53,
  "intervalo_alto": 30794.68,
  "intervalo_incluye_cero": false,
  "target_units": "ate",
  "interpretacion": "...",
  "source": "agent"
}
```

Este endpoint usa el agente por defecto. La herramienta local `estimate_causal_effect_tool` calcula el efecto con DoWhy y el agente interpreta magnitud, intervalo y conclusion. Para pruebas sin gastar tokens, envia `"use_agent": false`.

### Validar robustez del estimado

```http
POST /datasets/{file_name}/causal/refute
```

Body:

```json
{
  "outcome": "PriceEuro",
  "treatment": "treatment",
  "treatment_code": "df[\"treatment\"] = (df[\"TopSpeed_KmH\"] > 200).astype(int)\ndf = df.drop(columns=[\"TopSpeed_KmH\"])",
  "dot": "digraph { ... }",
  "metodo": "backdoor.linear_regression",
  "use_agent": true
}
```

Respuesta:

```json
{
  "file_name": "ElectricCarData_Clean.csv",
  "metodo_estimacion": "backdoor.linear_regression",
  "metodo_refutacion": "random_common_cause",
  "estimate": 20075.6,
  "new_effect": 20311.97,
  "cambio_absoluto": 236.36,
  "cambio_relativo": 0.0118,
  "p_valor": 0.9,
  "interpretacion": "...",
  "source": "agent"
}
```

Este endpoint usa el agente por defecto. La herramienta local `refute_estimate_tool` ejecuta `random_common_cause` con DoWhy y el agente interpreta la robustez. Para pruebas sin gastar tokens, envia `"use_agent": false`.

## Siguiente paso

Con este endpoint queda cubierto el flujo causal principal de la API.
