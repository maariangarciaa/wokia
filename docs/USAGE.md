# Guia de uso

Esta guia describe el flujo recomendado para probar la app de principio a fin.

## 1. Preparar el entorno

Activa el entorno virtual e instala dependencias:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configura una API key en `envs/groq.env` o `envs/gemini.env`.

## 2. Ejecutar la app

```powershell
streamlit run main.py
```

Abre la URL local que muestre Streamlit.

## 2.1 Ejecutar el backend opcional

La version Streamlit funciona sin backend. Para probar la API inicial:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Documentacion interactiva:

```text
http://localhost:8000/docs
```

Ejemplo de endpoint asistido:

```http
POST /datasets/{file_name}/assistant-summary
```

## 3. Cargar datos

En la pestana de datos puedes:

- seleccionar un archivo previamente subido;
- subir un CSV;
- subir un Excel.

Recomendacion: empieza con un dataset pequeno o mediano para que las llamadas al LLM sean mas rapidas.

## 4. Revisar el resumen

Usa el apartado de resumen para obtener:

- estructura general del dataset;
- tipos de variables;
- valores nulos;
- duplicados;
- sugerencias de nuevas variables.

La respuesta del agente debe ser breve, practica y centrada en el dataset cargado.

## 5. Generar graficos

En graficos puedes escribir peticiones como:

```text
Haz un grafico de dispersion de Range_Km en funcion de PriceEuro.
```

```text
Haz un boxplot del precio PriceEuro por tipo de carroceria BodyStyle.
```

La app usa el LLM para generar codigo de visualizacion y lo ejecuta localmente sobre el dataset cargado.

## 6. Explorar causalidad

Hay dos formas de iniciar el flujo causal:

- seleccionar manualmente una columna como tratamiento;
- escribir una pregunta causal para que la app proponga variables candidatas.

Despues el flujo permite:

- generar o confirmar la columna `treatment`;
- revisar diagnostico previo;
- generar el DAG;
- construir el modelo causal con DoWhy;
- evaluar identificabilidad;
- recomendar metodo de estimacion;
- estimar el efecto;
- validar robustez.

## 7. Consejos de prueba

- Usa nombres de columnas claros.
- Para causalidad, intenta que el tratamiento tenga dos grupos con suficientes observaciones.
- Si hay rate limit del proveedor LLM, espera a que se reinicie la cuota o cambia temporalmente de proveedor.
- Si una respuesta del LLM sale pobre, prueba con una pregunta mas especifica.
