import streamlit as st


def mostrar_introduccion():
    with st.container():
        st.markdown(
            """
            <div class="page-kicker">Ayuda</div>
            <h1 class="page-title">Como trabajar con Wokia</h1>
            <p class="page-subtitle">Una guia breve para entender el flujo de analisis y las capacidades principales del workspace.</p>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-title">1. Carga el dataset</div>
                    <p class="feature-text">Empieza con un archivo CSV o Excel. La app conserva el archivo seleccionado para que el resto de modulos trabajen sobre el mismo dataset.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-title">2. Revisa la calidad</div>
                    <p class="feature-text">Consulta estructura, tipos de variables, nulos, duplicados, correlaciones, outliers y posibles variables derivadas.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-title">3. Genera graficos</div>
                    <p class="feature-text">Describe visualizaciones en lenguaje natural y revisa el resultado directamente en la interfaz.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-title">4. Explora causalidad</div>
                    <p class="feature-text">Formula una pregunta causal, crea un tratamiento, valida un DAG y estima el efecto con herramientas especializadas.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title">Enfoque</div>', unsafe_allow_html=True)
        st.markdown(
            """
            Wokia esta pensada como una mesa de trabajo para analisis exploratorio asistido por IA. 
            Combina calculos deterministas, visualizacion y agentes con herramientas cuando el flujo necesita razonamiento paso a paso.
            """
        )

        st.markdown('<div class="section-title">Tecnologias</div>', unsafe_allow_html=True)
        st.markdown(
            """
            - Streamlit para la interfaz.
            - Pandas, NumPy, Matplotlib y Seaborn para analisis y visualizacion.
            - LangChain para agentes con herramientas.
            - DoWhy para el flujo de inferencia causal.
            - Modelos LLM por API configurados desde `.env`.
            """
        )
