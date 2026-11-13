import streamlit as st
import pandas as pd
import time
#from auto_doc.models.agent import PandasAgentFactory
from auto_doc.analysis.profile import (
    build_dataset_context as build_dataset_context_pure,
    summarize_duplicates,
    summarize_missing_values,
)
from auto_doc.models.causal_agent import CausalAgentFactory
from auto_doc.services.useful_services import load_file
# -----------------------------
# 💬 Consulta protegida al agente
# -----------------------------
import re

def build_dataset_context(df: pd.DataFrame) -> str:
    return build_dataset_context_pure(df)


def resumir_valores_nulos(df: pd.DataFrame) -> str:
    return summarize_missing_values(df)


def resumir_duplicados(df: pd.DataFrame) -> str:
    return summarize_duplicates(df)
    duplicated_mask = df.duplicated(keep=False)
    if not duplicated_mask.any():
        return "No se detectan registros duplicados exactos."

    duplicated_rows = df.loc[duplicated_mask].drop_duplicates()
    total = int(df.duplicated().sum())
    header = f"Se detectan {total} registros duplicados exactos. Filas duplicadas únicas:"
    impact = "Estos duplicados pueden inflar frecuencias, sesgar medias o dar más peso a observaciones repetidas durante el análisis."
    return f"{header}\n\n{duplicated_rows.to_markdown(index=False)}\n\n{impact}"


def consulta_contextual_segura(key, prompt, llm_runner, dataset_context, reintentos=1):
    cache_key = f"contextual_{key}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    prompt_con_contexto = f"""
Contexto real del dataset:
{dataset_context}

Instrucciones:
- Responde completamente en espanol.
- Usa solo la informacion del contexto real del dataset.
- No digas que no tienes acceso al dataset.
- No inventes columnas, filas ni valores.
- No incluyas codigo.
- Mantén los nombres de columnas exactamente como aparecen.

- No menciones `df`, DataFrame, tabla de nulos ni el proceso interno.
- No uses preambulos como "Sin embargo", "si se requiere", "en resumen" o "propuesta de nuevas variables".
- Responde directamente a la tarea, sin repetir la misma idea dos veces.
- Si no hay hallazgos, dilo en una sola frase breve.
- En sugerencias de nuevas variables, cada propuesta debe incluir:
  - nombre de variable nuevo en formato `snake_case`;
  - formula o regla de calculo usando columnas existentes;
  - utilidad en una frase corta.

Tarea:
{prompt}
"""

    intentos = 0
    while intentos <= reintentos:
        try:
            resultado = llm_runner.run(prompt_con_contexto)
            time.sleep(0.5)
            st.session_state[cache_key] = resultado
            return resultado
        except Exception as e:
            mensaje = str(e)
            if "429" in mensaje and "retry_delay" in mensaje:
                segundos = extraer_segundos_espera(mensaje)
                if segundos:
                    st.warning(f"Limite de uso alcanzado. Esperando {segundos} segundos antes de reintentar...")
                    time.sleep(segundos)
                    intentos += 1
                    continue
            return f"Error: {e}"

    return "Error persistente tras varios intentos. Intenta de nuevo mas tarde."

def consulta_segura(key, prompt, agent, reintentos=1):
    if key in st.session_state:
        return st.session_state[key]

    intentos = 0
    while intentos <= reintentos:
        try:
            resultado = agent.run(prompt)
            time.sleep(2)
            st.session_state[key] = resultado
            return resultado
        except Exception as e:
            mensaje = str(e)

            # Detectar el error 429 y tiempo sugerido
            if "429" in mensaje and "retry_delay" in mensaje:
                segundos = extraer_segundos_espera(mensaje)
                if segundos:
                    st.warning(f"Limite de uso alcanzado. Esperando {segundos} segundos antes de reintentar...")
                    time.sleep(segundos)
                    intentos += 1
                    continue

            # Otro tipo de error o ya ha reintentado
            return f"Error: {e}"

    return "Error persistente tras varios intentos. Intenta de nuevo mas tarde."


def extraer_segundos_espera(mensaje_error):
    """
    Extrae la cantidad de segundos desde un mensaje de error que contiene 'retry_delay { seconds: X }'
    """
    match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", mensaje_error)
    return int(match.group(1)) if match else None


import time
import streamlit as st

# -----------------------------
#  Interfaz principal
# -----------------------------

def mostrar_agente():
    with st.container():
        st.markdown(
            """
            <div class="page-kicker">Perfilado</div>
            <h1 class="page-title">Perfil estadistico</h1>
            <p class="page-subtitle">Revision rapida de estructura, calidad, relaciones, outliers y posibles variables utiles para modelado.</p>
            """,
            unsafe_allow_html=True,
        )

        if "file_path" not in st.session_state:
            st.error("No se ha subido ningun archivo. Por favor, vuelve atras y sube uno.")
            return

        file_path = str(st.session_state["file_path"])
        
        try:
            df = load_file(file_path)
        except Exception as e:
            st.error(f"Error al cargar el archivo: {e}")
            return

        st.session_state["df"] = df

        preview = df.head()
        st.markdown('<div class="section-title">Vista previa del dataset</div>', unsafe_allow_html=True)
        st.dataframe(preview)
        dataset_context = build_dataset_context(df)

        import io

        # Botón para crear el agente
        if st.button("Inicializar agente"):
            with st.spinner("Inicializando agente..."):
                factory = CausalAgentFactory()
                st.session_state["summary_llm"] = factory.llm_instance
            st.success("Agente inicializado correctamente")

        # Si el agente ya está listo
        if "summary_llm" in st.session_state:
            agent = st.session_state["summary_llm"]

            # Análisis general
            with st.expander("📋 Perfilado general del dataset"):

                prompt = """
                Rol:  
                Actúas como un analista de datos experto. Tu función es examinar un conjunto de datos estructurados y proporcionar un resumen técnico que describa su composición general.

                Objetivo:  
                Describir con precisión la estructura del dataset, incluyendo su tamaño y el tipo de variable asociada a cada columna, de forma comprensible y útil para un análisis posterior.

                Reglas:  
                - Escribe la respuesta completamente en español.  
                - NO traduzcas los nombres de las columnas ni de las variables; mantenlos tal como aparecen en el dataset.  
                - Identifica el número total de filas (excluyendo la columna de índice, si aplica) y el número total de columnas.  
                - Clasifica el tipo de variable de cada columna usando una de las siguientes categorías:
                - Variable numérica (continua o discreta)  
                - Variable categórica (nominal u ordinal)  
                - Variable booleana  
                - Variable de fecha o tiempo  
                - Otro tipo (especificar, si aplica)  
                - Usa comillas invertidas (``) para los nombres de las columnas.  
                - No incluyas fragmentos de código, explicaciones de métodos ni menciones a estructuras técnicas como "DataFrame".
                - Si la variable es numérica o categórica, DEBES indicar el subtipo correspondiente.

                Formato esperado:  
                El DataFrame contiene número de filas X y número de columnas Y.  

                Tipos de variables por columna:
                - `Columna1`: Variable de texto  
                - `Columna2`: Variable numérica (continua)  
                - ...
                """


                st.write(consulta_contextual_segura("perfil", prompt, agent, dataset_context))

            # Significado de columnas
            with st.expander("🔠 Significado de las columnas"):

                prompt = """
                Rol: Actúas como un analista de datos experto. Tu tarea es ayudar a un usuario a comprender a fondo el contenido de un conjunto de datos.  

                Objetivo:  
                Explicar con detalle y precisión el propósito de cada columna presente en el conjunto de datos, facilitando su comprensión general. La explicación debe estar en formato de lista.  

                Reglas:  
                - Existe un DataFrame cargado en la variable llamada `df`. Debes trabajar ÚNICAMENTE con ese DataFrame.  
                - Antes de redactar la respuesta final, ejecuta `python_repl_ast` para obtener y revisar:  
                - `list(df.columns)`  
                - `df.dtypes`  
                - NO inventes ni generes un DataFrame. Solo analiza el que ya está en la variable `df`.  
                - La respuesta debe estar escrita completamente en español.  
                - NO traduzcas los nombres de las columnas ni de las variables; mantenlos exactamente como aparecen en el dataset.  
                - Usa comillas invertidas (``) para destacar los nombres de las columnas.  
                - No incluyas fragmentos de código ni menciones al nombre del DataFrame en la explicación final.  
                - Evita lenguaje técnico innecesario.  
                - Explica cada columna de manera clara, ordenada, profesional y accesible para personas no expertas.  
                - Cada columna debe ser descrita con detalle, no con definiciones vagas ni superficiales.
                """

                st.write(consulta_contextual_segura("columnas", prompt, agent, dataset_context))

            # Valores nulos
            with st.expander("🧼 Valores nulos"):
                prompt = """
                Rol:
                Actúas como analista de datos experto. Tienes ACCESO DIRECTO a un DataFrame de pandas ya cargado en la variable `df` y DEBES usarlo para tu análisis.

                Objetivo:
                Redactar un informe profesional centrado en la calidad de los datos, específicamente sobre la presencia de valores nulos en el conjunto de datos cargado en `df`.

                Proceso (invisible para el lector):
                - Calcula el total de valores nulos y la cantidad y porcentaje de nulos por columna usando `df`.
                - Ordena de mayor a menor proporción de nulos.
                - Considera “proporción especialmente alta” cuando sea ≥ 10% (resáltalas en **negrita**).

                Reglas de redacción:
                - Escribe la respuesta completamente en español.
                - NO traduzcas los nombres de las columnas; escríbelos exactamente como aparecen y ponlos entre comillas invertidas (``).
                - No empieces con encabezados del tipo “Análisis de valores nulos:”; responde directamente.
                - Menciona únicamente las columnas que presenten valores nulos, indicando para cada una el número y el porcentaje.
                - Resalta en **negrita** las columnas con proporción de nulos ≥ 10%.
                - Evita lenguaje técnico innecesario y mantén un tono ejecutivo para tomadores de decisión.

                Restricciones de salida:
                - No incluyas fragmentos de código ni menciones a estructuras técnicas (como “DataFrame”, “NaN”, “isnull”, etc.).
                - No generes nuevos datos ni construyas objetos; utiliza exclusivamente `df` ya cargado.
                - Si no hay valores nulos, indícalo de forma breve y clara.

                Nota:
                No pidas más datos al usuario ni declares que no tienes acceso a `df`; ya lo tienes y debes usarlo.
                """

                st.markdown(resumir_valores_nulos(df))


            # Duplicados
            with st.expander("📑 Duplicados"):
                prompt = """
                Rol:
                Eres un analista de datos experto encargado de redactar un informe ejecutivo sobre la calidad de los datos.

                Objetivo:
                Detectar si existen registros duplicados en el conjunto de datos y, en caso afirmativo, mostrar solo una vez cada registro que aparece duplicado, evitando repeticiones innecesarias.

                Reglas de redacción:
                - Escribe completamente en español.
                - Si existen duplicados, preséntalos en una tabla en formato Markdown.
                - La tabla debe contener únicamente una vez cada fila duplicada, aunque aparezca varias veces en el dataset.
                - Tras la tabla, añade un párrafo breve y profesional explicando el posible impacto de los duplicados en el análisis de los datos.
                - Usa un lenguaje claro y accesible para personas sin conocimientos técnicos.

                Restricciones:
                - No incluyas fragmentos de código ni menciones técnicas como “DataFrame” o funciones de programación.
                - No inventes datos; usa únicamente la información real contenida en `df`.
                - Si no existen duplicados, indícalo de manera breve y clara.
                """

                st.markdown(resumir_duplicados(df))

            # Correlaciones numéricas
            with st.expander("Correlaciones numericas"):

                prompt = """
                Rol:  
                Actúas como un analista de datos experto con capacidad de ejecutar código en Python. Tu tarea es calcular y analizar la matriz de correlación entre las variables numéricas de un conjunto de datos.

                Pasos que debes seguir:

                1. Filtra únicamente las columnas numéricas del conjunto de datos.  
                2. Calcula la matriz de correlación utilizando la función `df.corr(numeric_only=True)`.  
                3. Convierte la matriz resultante como si fuera una TBLA para que pueda mostrarse correctamente, no la imprimas con formato Python.  
                4. Muestra primero esa tabla en formato Markdown.  
                5. A partir de la matriz, redacta un análisis en español que incluya:
                - Variables con correlación alta (mayor a 0.7 o menor a -0.7).  
                - Señales de posible multicolinealidad.  
                - Variables con correlación débil (cercana a 0).  
                - Cualquier relación inesperada o contraintuitiva.  
                - Variables que podrían ser redundantes.

                Restricciones:  
                - NO incluyas explicaciones del código ni suposiciones innecesarias sobre el significado de las columnas.  
                - Redacta el análisis final como un informe técnico corto y claro, en español.  
                - Muestra primero la tabla de correlación en formato TABLA y luego el análisis interpretativo.

                ⚠️ IMPORTANTE: Trabaja SIEMPRE con el DataFrame filtrado a solo columnas numéricas
                (df.select_dtypes(include=['number'])) antes de calcular la correlación. 
                NO incluyas columnas categóricas, texto o identificadores.
                """

                raw_output = consulta_contextual_segura("correlaciones", prompt, agent, dataset_context)

                # Elimina bloques de código ``` (y cualquier variante como ```markdown o ```python)
                clean_output = re.sub(r"```.*?\n", "", raw_output)  
                clean_output = clean_output.replace("```", "")     
                st.markdown(clean_output, unsafe_allow_html=True)


            # Sugerencias de nuevas features
            with st.expander("Sugerencias de nuevas variables"):
                prompt = """
                Rol:  
                Actúas como un analista de datos experto en ingeniería de características. Tu responsabilidad es identificar oportunidades para crear variables derivadas que realmente aporten valor al análisis de datos o mejoren el rendimiento de modelos predictivos.

                Objetivo:  
                Proponer nuevas variables que se puedan calcular lógicamente a partir de los datos existentes y que ofrezcan una mejora sustancial en términos de análisis, interpretación o predicción.

                Reglas:  
                - Escribe la respuesta completamente en español.  
                - NO traduzcas los nombres de las columnas ni de las variables; mantenlos exactamente como aparecen en el dataset.  
                - Sugiere solo variables que puedan derivarse directamente de los datos actuales.  
                - Por cada variable propuesta, explica con detalle:
                - **Nombre nuevo en codigo** en formato `snake_case`.
                - **Formula o regla de calculo** usando exclusivamente columnas existentes.
                - **Qué información nueva aporta**
                - **Por qué sería útil para el análisis**
                - **Cómo podría beneficiar a un modelo predictivo**
                - Resalta los nombres de las nuevas variables en **negrita**.  
                - Usa un lenguaje claro, profesional y orientado a negocio o ciencia de datos aplicada.

                Restricciones:  
                - Si no tienes acceso al contenido real de `df`, responde:  
                **"No puedo proponer nuevas variables sin conocer las columnas disponibles en el dataset."**
                - No propongas ejemplos genéricos ni ficticios.  
                - No inventes columnas que no existan.  
                - No incluyas código ni fórmulas matemáticas.  
                - No modifiques ni generes nuevas columnas en el DataFrame `df`.  
                - No ejecutes código ni realices cálculos.
                - NO empieces a redactar la respuesta con "Aquí hay algunas variables nuevas que se pueden derivar del DataFrame df:". Simplemente responde con las variables sugeridas directamente.

                IMPORTANTE: Todas tus respuestas deben estar redactadas en español. No respondas en inglés bajo ninguna circunstancia.  
                Antes de mostrar tu respuesta, asegúrate de que está escrita completamente en español. No debe contener texto en inglés ni estructuras de redacción típicas del inglés.
                """


                st.write(consulta_contextual_segura("features", prompt, agent, dataset_context))

            # Variable objetivo
            with st.expander("🎯 Posible variable objetivo para modelado"):
                prompt = """
                Rol:  
                Actúas como un analista de datos experto en modelado predictivo. Tu función es revisar cuidadosamente un conjunto de datos y proponer cuál columna sería la mejor candidata para usarse como **variable objetivo (target)** en un modelo supervisado de machine learning.

                Objetivo:  
                Identificar la columna más adecuada para ser predicha en un modelo, basándote en su función dentro del conjunto de datos, su relación con otras variables y su viabilidad práctica.

                Reglas:  
                - Escribe la respuesta completamente en español.  
                - NO traduzcas los nombres de las columnas ni de las variables; deben mantenerse exactamente como aparecen en el dataset.  
                - Analiza las características generales de todas las columnas disponibles.  
                - Considera si la columna:
                - Representa un resultado, estado futuro o evento predecible.  
                - Tiene relación dependiente con otras variables.  
                - Es relevante desde una perspectiva de negocio o análisis, y no es solo un identificador.  
                - Tiene una distribución y nivel de completitud que permitan su uso práctico.  

                Formato esperado:  
                - Menciona la variable candidata destacándola en **negrita**.  
                - A continuación, redacta un párrafo bien argumentado explicando por qué esa columna es una buena elección como variable objetivo.  
                - La explicación debe cubrir tanto criterios técnicos como de negocio.  
                - No se acepta una respuesta sin justificación.

                Restricciones:  
                - No propongas columnas de forma arbitraria.  
                - No selecciones columnas con muchos valores faltantes o sin relevancia.  
                - No incluyas fragmentos de código ni explicaciones técnicas complejas.  
                - Trabaja exclusivamente con la información contenida en el dataset disponible en la variable `df`.
                """


                st.write(consulta_contextual_segura("target", prompt, agent, dataset_context))

            # Outliers
            with st.expander("🚨 Valores atípicos (outliers)"):
                prompt = """
                Rol:  
                Actúas como un analista de datos experto con capacidad de ejecutar código en Python. Tienes acceso al DataFrame `df`. Tu tarea es detectar y reportar valores atípicos (outliers) de forma clara, precisa y profesional.

                Objetivo:  
                Identificar columnas con valores atípicos (especialmente en variables numéricas o de fecha), extraer al menos uno o dos valores concretos y explicar su impacto real en el análisis de datos, redactando de forma variada y específica.

                **Formato obligatorio de la salida: **
                Responde con una lista en formato Markdown, donde cada línea siga **estrictamente** esta estructura:
                - **``NombreDeColumna``**: valor atípico detectado: X (alto / bajo). Explicación breve y concreta sobre por qué es atípico y cómo podría distorsionar el análisis o la interpretación de los datos.

                **Detalles que debes incluir por cada línea:**
                - Muestra **uno o dos valores extremos detectados** por columna (sin mostrar todos).
                - Indica si el valor es **demasiado alto** o **demasiado bajo** respecto al rango habitual.
                - Usa una redacción fluida, profesional y **no repetitiva** (evita usar la misma frase para todas las columnas).
                - Adapta el impacto del outlier al contexto de negocio si es posible (por ejemplo, en precios, tiempos, velocidad, etc.).

                Método:  
                Aplica múltiples métodos estadísticos para detectar outliers (como IQR y z-score). Si un valor es detectado por **al menos uno de ellos**, inclúyelo como atípico. Considera especialmente los extremos de la distribución.

                Especial atención:  
                - Identifica valores atípicos que estén **muy por debajo o muy por encima** del resto, aunque no haya alta variabilidad.
                - Si una columna tiene pocos valores únicos, **evalúa conceptualmente** si los extremos son realmente inusuales (ej: en `Seats`, los valores 2 y 7 pueden ser atípicos aunque estén dentro del rango IQR).

                🚫 Restricciones:
                - No uses párrafos largos, escribe solo listas con guiones (`-`).
                - No agrupes columnas. Una línea por cada variable afectada.
                - No repitas frases como "se desvía significativamente del rango típico" en todas las líneas.
                - No incluyas fragmentos de código, fórmulas ni términos técnicos.
                - No inventes datos. Usa únicamente el contenido real del DataFrame `df`.

                Ejemplo esperado de salida:
                - **``PriceEuro``**: valor atípico detectado: 180781 (alto). Este precio es considerablemente más alto que el resto y puede influir de forma desproporcionada en los análisis de costos promedio.
                - **``Efficiency_WhKm``**: valor atípico detectado: 104 (bajo). Un valor tan bajo de consumo podría representar una medición inusual o un vehículo atípico, alterando las conclusiones sobre eficiencia general.
                """


                st.write(consulta_contextual_segura("outliers", prompt, agent, dataset_context))

        else:
            st.info("Haz clic en 'Inicializar agente' para comenzar el analisis.")
