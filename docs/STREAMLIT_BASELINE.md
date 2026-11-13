# Wokia Streamlit baseline

Fecha de congelacion: 2026-05-25

Esta version queda marcada como la baseline estable de Wokia en Streamlit.

## Alcance congelado

La version actual incluye:

- carga de CSV y Excel;
- perfilado/resumen asistido del dataset;
- visualizaciones generadas desde lenguaje natural;
- flujo completo de causalidad;
- configuracion de LLM mediante archivos `envs/*.env`;
- documentacion minima de instalacion y uso.

## Regla de mantenimiento

A partir de esta baseline, no se deberia modificar la logica de Streamlit salvo para:

- corregir bugs;
- arreglar errores de compatibilidad;
- actualizar documentacion;
- hacer ajustes pequenos de texto que no cambien el comportamiento.

Los cambios de arquitectura deben hacerse en una fase separada, manteniendo esta version como referencia funcional.

## Flujo manual de validacion

Antes de considerar que un cambio conserva la baseline, probar:

1. Ejecutar `streamlit run main.py`.
2. Cargar un CSV.
3. Revisar el perfilado estadistico.
4. Generar al menos un grafico.
5. Ejecutar causalidad con pregunta causal.
6. Ejecutar causalidad con tratamiento manual.
7. Confirmar que el DAG, modelo causal, estimacion y robustez funcionan.

## Siguiente fase recomendada

La siguiente fase no deberia ser redisenar mas Streamlit, sino preparar una separacion gradual:

1. Extraer funciones puras desde `modules/` hacia `auto_doc/`.
2. Crear un backend FastAPI minimo.
3. Crear un frontend React de Wokia.
4. Conectar React por modulos, usando esta baseline como referencia de comportamiento.
