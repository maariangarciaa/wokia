import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import re
import unicodedata
from auto_doc.analysis.charts import (
    build_chart_fallback as build_chart_fallback_pure,
    build_graph_context as build_graph_context_pure,
    normalize_text as normalize_text_pure,
    sanitize_generated_code as sanitize_generated_code_pure,
)
from auto_doc.models.causal_agent import CausalAgentFactory
from auto_doc.services.useful_services import load_file

def normalize_text(text: str) -> str:
    return normalize_text_pure(text)

def build_graph_context(df):
    return build_graph_context_pure(df)

def build_chart_fallback(user_input, df):
    return build_chart_fallback_pure(user_input, df)
    text = normalize_text(user_input)
    numeric_columns = list(df.select_dtypes(include="number").columns)
    pink = "rosa" in text or "pink" in text

    if "correlacion" in text or "correlación" in text or "correlation" in text:
        cmap = "RdPu" if pink else "coolwarm"
        return f"""
```python
numeric_df = df[{numeric_columns!r}]
corr = numeric_df.corr(numeric_only=True)
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(corr, annot=True, cmap='{cmap}', center=0, fmt='.2f', linewidths=0.5, ax=ax)
_ = ax.set_title('Correlation matrix')
_ = ax.tick_params(axis='x', rotation=45)
_ = ax.tick_params(axis='y', rotation=0)
```
"""

    if "boxplot" in text or "diagrama de caja" in text or "caja" in text:
        color = "#F4A6C1" if pink else "#A4C6E8"
        y_col = "PriceEuro" if "PriceEuro" in df.columns else numeric_columns[0]
        x_col = "BodyStyle" if "BodyStyle" in df.columns else df.select_dtypes(exclude="number").columns[0]
        return f"""
```python
fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(data=df, x='{x_col}', y='{y_col}', color='{color}', ax=ax)
_ = ax.set_title('{y_col} by {x_col}')
_ = ax.set_xlabel('{x_col}')
_ = ax.set_ylabel('{y_col}')
_ = ax.tick_params(axis='x', rotation=45)
```
"""

    return None

def sanitize_generated_code(code: str, user_input: str) -> str:
    return sanitize_generated_code_pure(code, user_input)
    text = normalize_text(user_input)
    cleaned = re.sub(r"plt\.show\(\)\s*;?", "", code)
    cleaned = re.sub(r"\.show\(\)\s*;?", "", cleaned)

    # Seaborn expects a palette name/list for `palette`, not a single hex color.
    cleaned = re.sub(r"palette\s*=\s*['\"]#([0-9A-Fa-f]{6})['\"]", r"color='#\1'", cleaned)

    if "rosa" in text or "pink" in text:
        cleaned = re.sub(r"color\s*=\s*['\"]#A4C6E8['\"]", "color='#F4A6C1'", cleaned)

    if ("correlacion" in text or "correlation" in text) and ("rosa" in text or "pink" in text):
        cleaned = re.sub(r"cmap\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)
        cleaned = re.sub(r"palette\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)
        if "sns.heatmap" in cleaned and "cmap=" not in cleaned:
            cleaned = re.sub(r"sns\.heatmap\(([^,\n\)]+),", r"sns.heatmap(\1, cmap='RdPu',", cleaned, count=1)

    if "correlacion" in user_input.lower() or "correlación" in user_input.lower():
        if "rosa" in user_input.lower() or "pink" in user_input.lower():
            cleaned = re.sub(r"cmap\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)
            cleaned = re.sub(r"palette\s*=\s*['\"][^'\"]+['\"]", "cmap='RdPu'", cleaned)

    return cleaned

def mostrar_graficos():
    with st.container():
        st.markdown(
            """
            <div class="page-kicker">Visualizacion</div>
            <h1 class="page-title">Visualizaciones</h1>
            <p class="page-subtitle">Describe el grafico que necesitas y Wokia generara una visualizacion limpia sobre el dataset cargado.</p>
            """,
            unsafe_allow_html=True,
        )

        if "file_path" not in st.session_state:
            st.error("No se ha subido ningún archivo. Por favor, vuelve atrás y sube uno.")
            return

        file_path = str(st.session_state["file_path"])
        
        try:
            df = load_file(file_path)
        except Exception as e:
            st.error(f"Error al cargar el archivo: {e}")
            return

        st.session_state["df"] = df

        if "chart_llm" not in st.session_state:
            st.markdown('<div class="section-title">Inicializar agente</div>', unsafe_allow_html=True)
            if st.button("Crear agente"):
                with st.spinner("Inicializando agente..."):
                    factory = CausalAgentFactory()
                    st.session_state["chart_llm"] = factory.llm_instance
                st.success("Agente inicializado correctamente")
                return
            else:
                st.info("Pulsa el boton para crear el agente.")
                return

        agent = st.session_state["chart_llm"]

        st.markdown('<div class="section-title">Pregunta al agente para graficar</div>', unsafe_allow_html=True)
        user_input = st.text_input("Por ejemplo: 'Haz un histograma de la columna edad'", key="grafico_input")

        if st.button("Enviar peticion"):
            if not user_input:
                st.warning("Por favor, escribe una pregunta.")
                return

            try:
                with st.spinner("El agente está generando el gráfico..."):

                    instrucciones = """
                    Eres un analista de datos experto en visualización, especializado exclusivamente en generar código Python para construir gráficos con matplotlib o seaborn dentro de aplicaciones de Streamlit. No estás capacitado para responder preguntas sobre estadísticas, análisis de datos, limpieza, modelos de machine learning, manipulación de DataFrames, ni ningún tema que no sea estrictamente la **construcción de gráficos**.

                    Si la solicitud no está relacionada con crear un gráfico, responde:
                    **"No estoy especializado para eso, pide otra cosa."**

                    Si la solicitud no está claramente relacionada con un gráfico específico, o es ambigua, irrelevante o irrespetuosa —por ejemplo: "haz un gráfico cualquiera", "haz lo que quieras", "dibuja cualquier cosa", "haz una mierda de gráfico", "lo que sea" o "elige tú las variables"— responde con:
                    **"No puedo generar un gráfico con esa petición. Por favor, sé claro y específico indicando qué columnas o tipo de gráfico deseas."**

                    Tu entorno ya tiene un DataFrame precargado llamado `df`. Tu única tarea es devolver el código necesario para construir la visualización que se te pide, cumpliendo estrictamente estas instrucciones:

                    1. Usa `matplotlib` o `seaborn` para construir el gráfico.
                    2. **No llames a `st.pyplot()` ni a `plt.show()`**. El entorno se encargará de mostrar la figura.
                    3. **No imprimas ni devuelvas** el resultado de funciones como `plt.title()`, `plt.axis()`, `plt.xlabel()`, etc. Si una función devuelve un valor, ignóralo o asígnalo a una variable:  
                    Ejemplo: `_ = plt.axis('equal')`.
                    4. Usa el color por defecto `'#A4C6E8'` en todos los elementos, **a menos que el usuario haya pedido explícitamente un color distinto**. Si el usuario especifica un color (por nombre o código hexadecimal), respétalo en el gráfico.
                    5. Si generas un gráfico tipo **pie chart**, usa:  
                    `wedgeprops={'edgecolor': 'black', 'linewidth': 1}`.
                    6. El código debe estar completamente en **inglés**, con sintaxis válida de Python.
                    7. **No uses español en ningún lugar del código** (ni variables, ni comentarios, ni cadenas).
                    8. Asegúrate de devolver el código dentro de un bloque correctamente formateado:
                    Tres comillas invertidas seguidas de "python", luego el código con saltos de línea, y cierra con otras tres comillas invertidas.
                    ```python  
                    # Your code  
                    ```
                    
                    Si el código no cumple alguno de estos puntos, será rechazado automáticamente.
                    """

                    entrada_agente = (
                        instrucciones
                        + "\n\nContexto real del dataset:\n"
                        + build_graph_context(df)
                        + "\n\nReglas adicionales: no uses herramientas, no ejecutes codigo, no expliques nada y devuelve solo un bloque ```python ... ``` usando columnas existentes. Para graficos de correlacion, usa solo columnas numericas con df.select_dtypes(include='number') o una lista explicita de columnas numericas.\n"
                        + "\n\nSolicitud del usuario:\n"
                        + user_input
                    )
                    respuesta = agent.run(entrada_agente)

                    # Asegurar respuesta como texto
                    if isinstance(respuesta, str):
                        codigo_bruto = respuesta
                    elif isinstance(respuesta, dict) and "output" in respuesta:
                        codigo_bruto = respuesta["output"]
                    else:
                        st.error("La respuesta del agente no es valida.")
                        return

                    # Arreglos menores de formato
                    codigo_bruto = codigo_bruto.replace("````", "```")  # Corrige comillas mal cerradas

                    # Extraer bloque de código
                    match = re.search(r"```(?:python)?\s*(.*?)```", codigo_bruto, re.DOTALL)


                    if not match:
                        # Evitar intentar ejecutar texto plano como código
                        st.warning("📭 No se generó ningún código gráfico válido.")
                        st.markdown("**Respuesta del agente:**")
                        st.code(codigo_bruto)
                        return

                    codigo_limpio = sanitize_generated_code(match.group(1).strip(), user_input)

                    # Limpiar cualquier figura activa
                    plt.close("all")

                    # Ejecutar el código en un entorno controlado
                    local_scope = {"df": df, "plt": plt, "sns": sns}
                    try:
                        exec(codigo_limpio, {}, local_scope)
                    except Exception as e:
                        fallback = build_chart_fallback(user_input, df)
                        if not fallback:
                            st.error(f"Error al ejecutar el codigo generado:\n{e}")
                            return

                        fallback_match = re.search(r"```(?:python)?\s*(.*?)```", fallback, re.DOTALL)
                        codigo_limpio = fallback_match.group(1).strip()
                        try:
                            plt.close("all")
                            exec(codigo_limpio, {}, local_scope)
                        except Exception as fallback_error:
                            st.error(f"Error al ejecutar el codigo generado:\n{fallback_error}")
                            return



                    import io

                    # Crear un buffer de imagen en memoria
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
                    buffer.seek(0)

                    # Mostrar el gráfico en pantalla
                    st.pyplot(plt.gcf())

                    # Botón de descarga
                    st.download_button(
                        label="Descargar grafico como PNG",
                        data=buffer,
                        file_name="grafico_generado.png",
                        mime="image/png"
                    )

                    # Cerrar figura para evitar conflictos futuros
                    plt.close("all")


            except Exception as e:
                st.error(f"Error al ejecutar el codigo generado: {e}")
