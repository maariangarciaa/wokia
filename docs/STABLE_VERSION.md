# Version estable

Fecha de cierre: 2026-05-25

Identificador: `wokia-streamlit-stable-2026-05-25`

## Estado

Esta version se considera una base funcional del proyecto:

- carga de CSV y Excel;
- resumen estadistico asistido;
- generacion de graficos;
- flujo de inferencia causal completo;
- configuracion de API keys fuera del codigo;
- dependencias principales recogidas en `requirements.txt`.

## Proveedor LLM recomendado

Para las pruebas recientes se ha usado Groq mediante API key.

Archivo esperado:

```text
envs/groq.env
```

Variables esperadas:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=tu-api-key
GROQ_MODEL_NAME=qwen/qwen3-32b
```

## Comprobacion manual recomendada

Antes de hacer cambios grandes, probar:

1. Cargar un CSV.
2. Generar resumen estadistico.
3. Pedir un grafico simple.
4. Ejecutar causalidad con pregunta causal.
5. Ejecutar causalidad seleccionando tratamiento manual.
6. Confirmar que se genera DAG, modelo, estimacion y robustez.

## Siguientes mejoras sugeridas

- Mantener esta version Streamlit como referencia funcional.
- Extraer logica pura desde `modules/` hacia `auto_doc/`.
- Crear un backend FastAPI minimo.
- Preparar un frontend React futuro sin romper esta baseline.

Ver tambien: `docs/STREAMLIT_BASELINE.md`.
