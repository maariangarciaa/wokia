# Wokia

Mini workbench de analisis de datos con asistencia LLM. Wokia permite cargar datasets tabulares, revisar su calidad, generar visualizaciones con lenguaje natural y explorar un flujo guiado de inferencia causal.

El proyecto incluye una interfaz React conectada a una API FastAPI y conserva la version anterior en Streamlit.

## Funcionalidades

- Carga de archivos CSV y Excel.
- Resumen estadistico asistido.
- Revision de nulos, duplicados, tipos de variables y primeras senales de calidad.
- Generacion de graficos a partir de instrucciones en lenguaje natural.
- Flujo de causalidad con seleccion de tratamiento, DAG, identificabilidad, estimacion y validacion de robustez.
- Soporte para proveedores LLM por API key: Groq o Gemini.

## Requisitos

- Python 3.12 recomendado.
- Node.js y npm para ejecutar la interfaz React.
- Una API key de Groq o Gemini.

## Instalacion

1. Crea y activa un entorno virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Instala las dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuracion del LLM

La app lee las claves desde la carpeta `envs/`.

### Opcion recomendada: Groq

```powershell
Copy-Item envs\groq.env.example envs\groq.env
```

Edita `envs/groq.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=tu-api-key
GROQ_MODEL_NAME=openai/gpt-oss-120b
```

### Opcion alternativa: Gemini

```powershell
Copy-Item envs\gemini.env.example envs\gemini.env
```

Edita `envs/gemini.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu-api-key
GEMINI_MODEL_NAME=gemini-2.0-flash-001
```

Los archivos `envs/*.env` estan ignorados por Git para evitar subir claves privadas.
Los modelos y cuotas de cada proveedor pueden cambiar; si un modelo no esta disponible, configura otro compatible con tu cuenta. El archivo `.env.example` es una referencia: la aplicacion carga los archivos reales de `envs/`.

## Ejecucion

### FastAPI

```powershell
uvicorn backend.main:app --reload --port 8000
```

Documentacion interactiva:

```text
http://localhost:8000/docs
```

Ejemplos JSON para Postman:

```text
docs/api_examples/
```

### React frontend

El frontend React esta en `frontend/` y consume FastAPI mediante el proxy `/api`.

En una terminal, deja FastAPI corriendo en `http://localhost:8000`. En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Despues abre:

```text
http://127.0.0.1:5173
```

Sube un CSV o Excel desde la pantalla inicial. Los archivos cargados se guardan localmente en `auto_doc/files/`, que Git ignora; no se incluyen datasets de ejemplo en el repositorio.

### Version anterior en Streamlit

```powershell
streamlit run main.py
```

## Estructura principal

- `main.py`: entrada de la app y navegacion.
- `modules/`: paginas de Streamlit.
- `auto_doc/models/causal_agent.py`: configuracion del LLM y agentes.
- `auto_doc/causal/`: herramientas auxiliares para DAG, diagnostico y flujo causal.
- `auto_doc/services/`: carga de archivos, prompts y servicios reutilizables para la API.
- `backend/`: API FastAPI para datasets, graficos, resumen asistido y flujo causal.
- `frontend/`: interfaz React conectada a FastAPI.
- `envs/`: plantillas y archivos locales de API keys.
- `docs/`: documentacion de uso y notas de version estable.

## Flujo causal en FastAPI

El flujo causal principal esta disponible como endpoints independientes:

```text
candidates -> hypotheses -> treatment -> dag -> identify -> method -> estimate -> refute
```

Partes que usan LLM/agente por defecto:

- `hypotheses`
- `treatment`
- `dag`
- `method`
- `estimate`
- `refute`

Partes deterministas:

- `candidates`
- `identify`

Los endpoints con `use_agent` aceptan `false` para pruebas sin gastar tokens.

## Documentacion

- Guia de uso: `docs/USAGE.md`
- Version estable: `docs/STABLE_VERSION.md`
- Baseline Streamlit congelada: `docs/STREAMLIT_BASELINE.md`
- Backend FastAPI: `docs/BACKEND.md`
- Ejemplos Postman: `docs/api_examples/` (requieren aportar el dataset correspondiente).
- Frontend React: `docs/FRONTEND.md`

## Limites del prototipo

Wokia es un proyecto exploratorio, no una herramienta de produccion. Las respuestas del LLM pueden contener errores y deben revisarse. Los resultados causales dependen del DAG, los datos y los supuestos elegidos; una correlacion o una prueba de robustez no demuestran causalidad. No todos los metodos de estimacion son adecuados para cualquier analisis.

La aplicacion ejecuta codigo Python generado por el modelo y admite codigo en algunas peticiones de la API. Ejecutala solo en un entorno local de confianza, sin exponer la API a Internet, y revisa el codigo generado. El tratamiento de datos enviados al LLM depende de la configuracion y condiciones del proveedor: no cargues datos sensibles sin evaluar su uso.

## Wokia en acción

[![Ver demostración de Wokia](docs/images/wokia-demo.png)](PEGA_AQUI_EL_ENLACE_DEL_VIDEO)

Haz clic en la imagen para ver la demostración.