import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar configuraciones desde archivos .env especificos
BASE_DIR = Path(__file__).parent
MISTRAL_ENV_PATH = BASE_DIR / "envs" / "mistral.env"
GEMINI_ENV_PATH = BASE_DIR / "envs" / "gemini.env"
GROQ_ENV_PATH = BASE_DIR / "envs" / "groq.env"

load_dotenv(MISTRAL_ENV_PATH)
load_dotenv(GEMINI_ENV_PATH)
load_dotenv(GROQ_ENV_PATH)

# Proveedor LLM activo
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Configuracion para Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1")
MISTRAL_MODEL_NAME = os.getenv("MISTRAL_MODEL_NAME", "mistral-small")

# Configuracion para Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-001")

# Configuracion para Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")

# Validar las variables de entorno obligatorias segun el proveedor activo
if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("The 'GEMINI_API_KEY' is missing in the gemini.env file.")
if LLM_PROVIDER == "gemini" and not GEMINI_MODEL_NAME:
    raise ValueError("The 'GEMINI_MODEL_NAME' is missing in the gemini.env file.")
if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
    raise ValueError("The 'GROQ_API_KEY' is missing in the groq.env file.")
if LLM_PROVIDER == "groq" and not GROQ_MODEL_NAME:
    raise ValueError("The 'GROQ_MODEL_NAME' is missing in the groq.env file.")
if LLM_PROVIDER not in {"gemini", "groq"}:
    raise ValueError("The 'LLM_PROVIDER' must be 'gemini' or 'groq'.")
