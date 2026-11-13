import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import json
from auto_doc.analysis.agent_outputs import parse_treatment_code_response
from auto_doc.analysis.causal import (
    dag_input_summary,
    outcome_by_treatment,
    treatment_balance,
    treatment_ttest,
)
from auto_doc.analysis.causal_workflow import create_manual_treatment, prepare_outcome
from auto_doc.analysis.causal_modeling import build_causal_model_from_dot
from auto_doc.causal.dag import generate_dag
from auto_doc.causal.tools import make_candidate_variables_tool
from auto_doc.models.causal_agent import CausalAgentFactory, CausalLLM
from auto_doc.services.useful_services import load_file

from auto_doc.services.prompts import (
    generar_prompt_codigo_tratamiento,
    generar_prompt_hipotesis,
    generar_prompt_variables_relacionadas,
    generar_prompt_dag_con_datos,
    generar_prompt_identificacion_efecto_seguro,
    generar_prompt_recomendar_metodo_critico,
    generar_prompt_interpretar_estimacion_causal,
    generar_prompt_validacion_robustez,
    generar_descripcion_dataset,
)

def mostrar_inferencia_causal():
    st.markdown(
        """
        <div class="page-kicker">Causalidad</div>
        <h1 class="page-title">Exploracion causal</h1>
        <p class="page-subtitle">Formula una hipotesis, define un tratamiento y estima efectos con un flujo guiado de inferencia causal.</p>
        """,
        unsafe_allow_html=True,
    )

    if "file_path" not in st.session_state:
        st.error("⚠️ No se ha subido ningún archivo. Por favor, vuelve atrás y sube uno.")
        return

    file_path = str(st.session_state["file_path"])
        
    try:
        df = load_file(file_path)
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {e}")
        return

    st.session_state["df"] = df

    st.markdown('<div class="section-title">Tratamiento o pregunta causal</div>', unsafe_allow_html=True)

    opcion = st.radio(
        "¿Quieres seleccionar una columna como tratamiento?",
        ("Sí, seleccionar tratamiento", "No, formular una pregunta causal")
    )

    if "modo_tratamiento" not in st.session_state:
        st.session_state["modo_tratamiento"] = opcion
    elif st.session_state.get("modo_tratamiento") != opcion:
        for clave in [
            "pregunta_causal", "candidatas", "candidatas_encontradas",
            "variable_candidata", "variable_objetivo", "hipotesis_usuario",
            "confirmado", "dag_dot_generado", "modo_edicion_dag", "dag_dot",
            "dag_confirmado", "causal_model", "identified_estimand",
            "backdoor_variables", "respuesta_identificabilidad",
            "respuesta_metodo_recomendado", "metodo_recomendado",
            "justificacion_metodo", "metodo_seleccionado",
            "interpretacion_causalidad", "validacion_robustez"
        ]:
            st.session_state.pop(clave, None)
        st.session_state["modo_tratamiento"] = opcion

    if opcion == "Sí, seleccionar tratamiento":
        tratamiento = st.selectbox("Selecciona la columna de tratamiento:", df.columns)

        if tratamiento:
            treatment_result = create_manual_treatment(df, tratamiento)
            df_tratado = treatment_result.df_tratado

            if not treatment_result.was_binary:
                st.warning("⚠️ La columna seleccionada no es binaria. Se convertirá automáticamente a una variable binaria.")

            st.session_state["tratamiento"] = tratamiento
            st.session_state["df_tratado"] = df_tratado
            st.session_state["treatment"] = treatment_result.treatment_col

            st.success(f"Columna seleccionada como tratamiento: **{tratamiento}** (convertida a binaria)")
            st.info(f"""
                 **Codificación aplicada a `{tratamiento}`:**
                - Valor **1** → `{treatment_result.value_1}`
                - Valor **0** → `{treatment_result.value_0}`
            """)

            # Selección de outcome tras tratamiento
            outcome = st.selectbox(
                "Selecciona la variable objetivo (resultado):",
                [col for col in df.columns if col != tratamiento],
                key="seleccion_outcome"
            )

            if outcome:
                outcome_result = prepare_outcome(df, df_tratado, outcome)
                df_tratado = outcome_result.df_tratado
                st.session_state["df_tratado"] = df_tratado

                if outcome_result.was_converted:
                    st.warning("⚠️ La variable objetivo es binaria pero no está codificada como 0 y 1. Se convertirá automáticamente.")
                    st.info(f"""
                         **Codificación aplicada a `{outcome}`:**
                        - Valor **1** → `{outcome_result.value_1}`
                        - Valor **0** → `{outcome_result.value_0}`
                    """)

                if outcome_result.is_valid:
                    st.session_state["variable_objetivo"] = outcome
                    st.success(f"Variable objetivo seleccionada: **{outcome}**")

                    if st.button("✅ Confirmar tratamiento y variable objetivo"):
                        st.session_state["confirmado"] = True

                        if "causal_agent" not in st.session_state:
                            with st.spinner("Inicializando agente..."):
                                factory = CausalAgentFactory()
                                st.session_state["causal_agent"] = factory.create_agent(df_tratado)

                        st.success("Tratamiento y outcome confirmados. Puedes continuar con el análisis causal.")
                else:
                    st.error("❌ La variable objetivo debe ser numérica o binaria. Selecciona otra.")

    else:
        pregunta_causal = st.text_input("Formula tu pregunta causal (por ejemplo: ¿Qué influye en el precio?)")
        if pregunta_causal:
            st.session_state["pregunta_causal"] = pregunta_causal

            if "candidatas" not in st.session_state and "candidatas_encontradas" not in st.session_state:
                if st.button("🔍 Encontrar variables candidatas"):
                    with st.spinner("Analizando variables candidatas..."):
                        response = make_candidate_variables_tool(df).run(pregunta_causal)

                    # Limpiar el texto: extraer solo la parte entre llaves
                    match = re.search(r"\{.*\}", response, re.DOTALL)
                    if match:
                        json_text = match.group(0)
                        try:
                            parsed = json.loads(json_text)
                            st.session_state["variable_objetivo"] = parsed["objetivo"]
                            st.session_state["candidatas"] = parsed["candidatas"]
                            st.session_state["candidatas_encontradas"] = True
                        except json.JSONDecodeError as e:
                            st.error("❌ No se pudo interpretar la respuesta del agente como JSON válido.")
                            st.code(json_text)
                    else:
                        st.error("❌ No se encontró un bloque JSON en la respuesta del agente.")
                        st.code(response)


    # Selección de variable candidata
    if st.session_state.get("candidatas_encontradas"):
        candidatas = st.session_state["candidatas"]

        st.subheader("Variables candidatas encontradas")
        seleccion_opcion = st.radio(
            "Selecciona cómo deseas elegir la variable para el análisis causal:",
            ("Seleccionar una de las variables candidatas sugeridas", "Quiero seleccionar otra variable manualmente"),
            key="opcion_variable_causal"
        )

        if seleccion_opcion == "Seleccionar una de las variables candidatas sugeridas":
            variable_candidata = st.radio("Selecciona una de las variables candidatas:", options=candidatas, key="seleccion_candidata")
        else:
            columnas_disponibles = [col for col in df.columns if col != st.session_state.get("variable_objetivo")]
            variable_candidata = st.selectbox("Selecciona cualquier otra variable del dataset:", options=columnas_disponibles, key="seleccion_manual")

        if variable_candidata:
            st.session_state["variable_candidata_temp"] = variable_candidata
            st.info(f"Has seleccionado: **{variable_candidata}**. Pulsa el botón para continuar.")

            if st.button("Confirmar variable candidata"):
                st.session_state["variable_candidata"] = variable_candidata
                # Eliminar hipótesis previas si cambió la variable
                st.session_state.pop("lista_hipotesis", None)

    # Hipótesis
    if "variable_candidata" in st.session_state and "variable_objetivo" in st.session_state:
        vi = st.session_state["variable_candidata"]
        vo = st.session_state["variable_objetivo"]

        st.markdown(f"🔎 Se analizará si **{vi}** tiene un efecto causal sobre **{vo}**.")
        st.subheader("Sugerencias de hipótesis causales")

        if "lista_hipotesis" not in st.session_state:
            prompt = generar_prompt_hipotesis(vo, vi, generar_descripcion_dataset(df))


            with st.spinner("Generando hipótesis..."):
                sugerencias = CausalLLM().run(prompt)

            st.session_state["lista_hipotesis"] = [
                linea.strip("-• ").strip()
                for linea in sugerencias.strip().split("\n")
                if linea.strip() and not linea.lower().startswith("aquí hay")
            ]

        opciones = st.session_state["lista_hipotesis"] + ["Quiero escribir mi propia hipótesis"]

        seleccion = st.radio(
            "Selecciona una hipótesis sugerida o escribe la tuya propia:",
            options=opciones,
            key="seleccion_hipotesis_radio"
        )

        if seleccion == "Quiero escribir mi propia hipótesis":
            hipotesis_usuario = st.text_area(
                "Escribe tu hipótesis causal:",
                placeholder=f"Ejemplo: A mayor {vi}, mayor será el {vo}...",
                key="hipotesis_input"
            )
            if hipotesis_usuario:
                st.session_state["hipotesis_usuario"] = hipotesis_usuario
                st.success("✅ Hipótesis registrada.")
        else:
            st.session_state["hipotesis_usuario"] = seleccion
            st.success(f"✅ Hipótesis seleccionada: *{seleccion}*")
        
    # Paso siguiente: Confirmar hipótesis y generar tratamiento
    if "hipotesis_usuario" in st.session_state:
        st.subheader("Confirmar hipótesis para generar la columna de tratamiento")
        if st.button("Confirmar hipótesis y generar columna treatment"):
            hipotesis = st.session_state["hipotesis_usuario"]

            prompt_codigo = generar_prompt_codigo_tratamiento(hipotesis)
            with st.spinner("Generando código para la columna de tratamiento..."):
                agente = CausalAgentFactory().create_agent(
                    df,
                    allowed_tool_names=["python_repl_ast"],
                    max_iterations=4,
                )
                respuesta = agente.run(prompt_codigo)

            try:
                parsed_response = parse_treatment_code_response(respuesta)
                explicacion = parsed_response.explicacion
                codigo = parsed_response.codigo

                if "ERROR" in explicacion or not codigo:
                    st.error("❌ No se pudo generar la columna de tratamiento con esta hipótesis.")
                    st.markdown(f"**Motivo:** {explicacion}")
                else:
                    df_base = df.copy()
                    namespace = {"df": df_base}
                    exec(codigo, namespace)
                    df_tratado = namespace["df"]
                    st.session_state["df_tratado"] = df_tratado
                    st.session_state["confirmado"] = True  
                    st.session_state["treatment"] = "treatment"

                    st.success("✅ Columna 'treatment' generada y aplicada al DataFrame.")
                    st.markdown(f"**Explicación:** {explicacion}")
                    st.markdown("🔍 Así se ve el dataset con la nueva columna `treatment`:")
                    st.dataframe(df_tratado.head())

                    # Reinicializar agente con df actualizado
                    with st.spinner("🔄 Reinicializando agente con el DataFrame actualizado..."):
                        factory = CausalAgentFactory()
                        agent = factory.create_agent(df_tratado)
                        st.session_state["causal_agent"] = agent

            except json.JSONDecodeError:
                st.error("❌ No se pudo interpretar la respuesta como JSON válido.")
                st.code(respuesta)
            except ValueError:
                st.error("❌ No se encontró JSON válido en la respuesta del agente.")
                st.code(respuesta)

    # Diagnóstico de viabilidad causal
    if (
    st.session_state.get("confirmado") and
    "df_tratado" in st.session_state and
    "variable_objetivo" in st.session_state
    ):
        df = st.session_state["df_tratado"]
        variable_objetivo = st.session_state["variable_objetivo"]

        st.subheader("📈 Diagnóstico previo al análisis causal")

        # Gráfico de barras de tratamiento
        st.markdown("### Distribución de grupos de tratamiento")
        fig, ax = plt.subplots(figsize=(5, 3.5))  # Tamaño intermedio y uniforme
        df["treatment"].value_counts().sort_index().plot(kind="bar", ax=ax, color=["#4C72B0", "#55A868"])
        ax.set_xlabel("Grupo de tratamiento (0 = control, 1 = tratado)")
        ax.set_ylabel("Número de observaciones")
        ax.set_title("Distribución de observaciones por grupo")
        ax.tick_params(axis='x', rotation=0)

        # Mostrar imagen en Streamlit
        import io
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        st.image(buf, width=400)

        # Análisis de balance entre grupos
        st.markdown("### ¿Está desbalanceado?")
        balance = treatment_balance(df, "treatment")
        counts = balance["counts"]
        porcentajes = balance["percentages"]

        texto_balance = "\n".join([
            f"- Grupo {idx}: {row} observaciones ({porcentajes[idx]:.1f}%)"
            for idx, row in counts.items()
        ])
        st.markdown(texto_balance)

        if balance["has_small_group"]:
            st.warning("⚠️ Uno de los grupos tiene menos de 10 observaciones. Esto puede dificultar el análisis causal.")

        if balance["is_unbalanced"]:
            st.info("ℹ️ Los grupos están notablemente desbalanceados. Considera métodos robustos de estimación o recolección adicional de datos.")
        else:
            st.success("✅ Los grupos de tratamiento están razonablemente balanceados.")

        # Estadísticas descriptivas
        st.markdown("### Estadísticas de la variable objetivo por grupo")
        resumen = outcome_by_treatment(df, variable_objetivo, "treatment")
        st.dataframe(resumen.style.format("{:.2f}"))

        # Boxplot
        st.markdown("### Distribución de la variable objetivo por grupo de tratamiento")
        fig2, ax2 = plt.subplots(figsize=(5, 3.5))  # Mismo tamaño que el gráfico anterior
        sns.boxplot(x="treatment", y=variable_objetivo, data=df, ax=ax2)
        ax2.set_xlabel("Grupo de tratamiento")
        ax2.set_ylabel(variable_objetivo)
        ax2.set_title("Distribución del precio por tratamiento")
        fig2.tight_layout()

        buf2 = io.BytesIO()
        fig2.savefig(buf2, format="png", bbox_inches="tight")
        st.image(buf2, width=400)

        # Test de diferencia
        test_result = treatment_ttest(df, variable_objetivo, "treatment")
        t_stat = test_result["t_stat"]
        p_val = test_result["p_value"]

        st.markdown("### Test estadístico de diferencia")
        st.markdown(f"- Estadístico t: `{t_stat:.2f}`")
        st.markdown(f"- Valor p: `{p_val:.5f}`")

        if p_val < 0.05:
            st.success("✅ La diferencia es estadísticamente significativa (p < 0.05).")
        else:
            st.info("ℹ️ No se detectó diferencia estadísticamente significativa.")

    # Paso 2: Visualización y construcción del DAG
    if (
        st.session_state.get("confirmado") and
        "df_tratado" in st.session_state and 
        "variable_objetivo" in st.session_state
    ):

        df_tratado = st.session_state["df_tratado"]

        st.subheader("🧭 Generación DAG (Gráfico de Supuestos)")

        if "dag_dot_generado" not in st.session_state:
            if st.button("🚀 Generar DAG automáticamente con ayuda del agente"):
                df = st.session_state["df_tratado"]
                outcome = st.session_state["variable_objetivo"]
                treatment = "treatment"

                # Cálculos previos
                resumen = dag_input_summary(df, outcome, treatment)

                with st.spinner("Generando DAG..."):
                    prompt_dag = generar_prompt_dag_con_datos(resumen)
                    causal_agent_dag = CausalAgentFactory().create_agent(
                        df_tratado,
                        allowed_tool_names=["generate_dag"],
                        max_iterations=2,
                    )
                    respuesta = causal_agent_dag.run(prompt_dag)
                    match = re.search(r"(digraph\s*\{.*\})", respuesta, re.DOTALL)
                    dot_code = match.group(1).strip() if match else generate_dag(json.dumps(resumen))

                    st.session_state["dag_dot_generado"] = dot_code
                    st.session_state["modo_edicion_dag"] = False
                    st.session_state["dag_dot"] = None
                    #st.experimental_rerun()  # 🔁 Forzar recarga para que aparezca el gráfico

        # Mostrar DAG generado solo si existe y no se está editando
        if "dag_dot_generado" in st.session_state and not st.session_state.get("modo_edicion_dag", False):
            dot_code = st.session_state["dag_dot_generado"]
            if dot_code.strip():  # Asegura que no esté vacío
                st.markdown("### 📊 Propuesta automática del DAG")
                st.graphviz_chart(dot_code)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirmar grafo"):
                        st.session_state["dag_dot"] = dot_code
                        st.session_state["dag_confirmado"] = True
                        st.success("✅ DAG confirmado. Puedes continuar.")
                with col2:
                    if st.button("✏️ Editar grafo"):
                        st.session_state["modo_edicion_dag"] = True


        # Edición del DAG
        if st.session_state.get("modo_edicion_dag", False):
            with st.form("editar_dag"):
                dot_editado = st.text_area(
                    "Edita el DAG en formato DOT:",
                    value=st.session_state["dag_dot_generado"],
                    height=220,
                    key="input_dag_editado"
                )
                submitted = st.form_submit_button("💾 Aplicar edición (previsualizar)")

            if submitted:
                st.session_state["dag_editado_temporal"] = dot_editado
                st.success("✅ Cambios aplicados. Revisa el gráfico y confirma si estás conforme.")

            if "dag_editado_temporal" in st.session_state:
                st.markdown("### 📊 Visualización del DAG editado")
                st.graphviz_chart(st.session_state["dag_editado_temporal"])

                if st.button("✅ Confirmar grafo editado"):
                    st.session_state["dag_dot"] = st.session_state["dag_editado_temporal"]
                    st.session_state["modo_edicion_dag"] = False
                    del st.session_state["dag_editado_temporal"]
                    st.session_state["dag_confirmado"] = True
                    st.success("✅ El DAG editado ha sido confirmado como definitivo.")

    # Paso 3: Construcción del modelo DoWhy
    if (
        "df_tratado" in st.session_state and 
        "variable_objetivo" in st.session_state and 
        "dag_dot" in st.session_state and 
        "dag_confirmado" in st.session_state and 
        st.session_state["dag_confirmado"]
    ):
        st.subheader("🏗️ Construcción del modelo causal")
        st.markdown("### DAG utilizado para el modelo")
        st.graphviz_chart(st.session_state["dag_dot"])

        if st.button("🧠 Generar modelo causal con DoWhy"):
            with st.spinner("Construyendo modelo causal..."):
                try:
                    dot_code = st.session_state["dag_dot"]
                    build_result = build_causal_model_from_dot(
                        df=st.session_state["df_tratado"],
                        treatment_col=st.session_state["treatment"],
                        outcome_col=st.session_state["variable_objetivo"],
                        dot_code=dot_code,
                    )

                    st.session_state["nx_graph"] = build_result.graph
                    st.session_state["causal_model"] = build_result.model
                    st.success("✅ Modelo causal construido con éxito.")
                    st.markdown("### 📄 Resumen del modelo")
                    st.markdown(f"- **Tratamiento:** `{st.session_state['treatment']}`")
                    st.markdown(f"- **Resultado:** `{st.session_state['variable_objetivo']}`")
                    st.markdown(f"- **Nº observaciones:** {len(st.session_state['df_tratado'])}")

                except Exception as e:
                    st.error("❌ Error al construir el modelo causal.")
                    st.exception(e)

  # Paso 4: Identificación del efecto causal
    if "causal_model" in st.session_state:

        if st.button("Evaluar identificabilidad del efecto causal con el agente"):
            with st.spinner("Ejecutando diagnóstico..."):
                try:
                    prompt = generar_prompt_identificacion_efecto_seguro()
                    response = st.session_state["causal_agent"].run(prompt)

                    # Guardar la respuesta del agente para mostrarla incluso después
                    st.session_state["respuesta_identificabilidad"] = response

                    # Paso necesario de DoWhy
                    model = st.session_state["causal_model"]
                    identified_estimand = model.identify_effect()
                    backdoors = identified_estimand.get_backdoor_variables()
                    st.session_state["identified_estimand"] = identified_estimand
                    st.session_state["backdoor_variables"] = backdoors

                except Exception as e:
                    st.error("❌ El agente no pudo ejecutar la evaluación.")
                    st.exception(e)

        # Mostrar la respuesta del agente si ya existe
        if "respuesta_identificabilidad" in st.session_state:
            response = st.session_state["respuesta_identificabilidad"]

            # Limpiar texto
            cleaned = (
                response.replace("```json", "")
                        .replace("```", "")
                        .replace("````json", "")
                        .replace("````", "")
                        .strip()
            )

            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    criterio = parsed.get("criterio")
                    backdoors = parsed.get("backdoor_variables", [])
                    justificacion = parsed.get("justificacion", "")

                    st.session_state["backdoor_variables"] = backdoors

                    st.markdown("### Diagnóstico de identificabilidad")
                    st.markdown(f"**Criterio usado:** `{criterio}`")
                    st.markdown(f"**Variables de ajuste:** `{backdoors}`")
                    st.markdown(f"**Justificación:** {justificacion}")

                except json.JSONDecodeError:
                    st.error("❌ JSON malformado. Revisa la estructura.")
                    st.code(cleaned)
            else:
                st.error("❌ No se encontró un bloque JSON válido.")
                st.code(response)

    # Paso 5: Método de estimación
    if (
    "causal_model" in st.session_state and 
    "backdoor_variables" in st.session_state and 
    "causal_agent" in st.session_state and
    "identified_estimand" in st.session_state
    ):
        st.subheader("📌 Recomendación del método de estimación")

        if st.button("Recomendar mejor método de estimación causal"):
            with st.spinner("🔍 Analizando dataset y variables de ajuste..."):
                try:
                    treatment = st.session_state["treatment"]
                    backdoors = st.session_state["backdoor_variables"]
                    prompt = generar_prompt_recomendar_metodo_critico(treatment, backdoors)

                    response = st.session_state["causal_agent"].run(prompt) 
                    st.session_state["respuesta_metodo_recomendado"] = response # guardar respuesta

                    match = re.search(r"\{.*\}", response, re.DOTALL)
                    if match:
                        resultado = json.loads(match.group(0))
                        metodo = resultado.get("metodo_recomendado")
                        justificacion = resultado.get("justificacion", "")

                        if metodo:
                            st.session_state["metodo_recomendado"] = metodo
                            st.session_state["justificacion_metodo"] = justificacion
                        else:
                            st.session_state["metodo_recomendado"] = None
                            st.session_state["justificacion_metodo"] = None
                    else:
                        st.session_state["metodo_recomendado"] = None
                        st.session_state["justificacion_metodo"] = None

                except Exception as e:
                    st.error("❌ Error al obtener la recomendación del agente.")
                    st.exception(e)

        # Mostrar contenido si ya existe
        if "metodo_recomendado" in st.session_state and st.session_state["metodo_recomendado"]:
            metodo = st.session_state["metodo_recomendado"]
            justificacion = st.session_state["justificacion_metodo"]

            st.markdown("### Método recomendado por el agente:")
            st.markdown(f"<h2 style='color:#4CAF50; font-size:32px;'>🔎 {metodo}</h2>", unsafe_allow_html=True)
            st.markdown("**Justificacion:**")
            st.markdown(justificacion)

            # Mostrar el selectbox
            metodos_disponibles = [
                "backdoor.linear_regression",
                "backdoor.propensity_score_matching",
                "backdoor.propensity_score_weighting",
                "backdoor.distance_matching",
                "backdoor.propensity_score_stratification",
                "iv_instrument_name",
                "iv.regression_discontinuity"

            ]

            metodo_sugerido = metodo

            st.markdown("---")
            st.markdown("### 🧰 Selecciona el método que deseas usar para la estimación:")
            opcion = st.selectbox(
                "Método de estimación causal:",
                options=metodos_disponibles,
                index=metodos_disponibles.index(metodo_sugerido) if metodo_sugerido in metodos_disponibles else 0,
                help="Puedes aceptar el método recomendado o seleccionar uno diferente manualmente."
            )

            st.session_state["metodo_seleccionado"] = opcion
            st.success(f"📌 Método seleccionado para estimación: `{opcion}`")

   # Paso 6: Estimación del efecto causal
    if (
        "causal_model" in st.session_state and 
        "identified_estimand" in st.session_state and 
        "metodo_seleccionado" in st.session_state 
    ):
        st.subheader("📐 Estimación del efecto causal")

        if st.button("El agente realizará la estimación y la interpretará"):
            with st.spinner("El agente está estimando el efecto causal..."):
                try:
                    if "causal_agent" not in st.session_state:
                        st.error("❌ No se ha inicializado el agente causal.")
                        st.stop()

                    if "treatment" not in st.session_state or "variable_objetivo" not in st.session_state:
                        st.error("❌ Faltan las columnas de tratamiento o resultado en session_state.")
                        st.stop()

                    causal_agent = st.session_state["causal_agent"]
                    treatment_col = st.session_state["treatment"]
                    outcome_col = st.session_state["variable_objetivo"]
                    metodo = st.session_state["metodo_seleccionado"]

                    prompt_interpretacion = generar_prompt_interpretar_estimacion_causal(
                        treatment_col=treatment_col,
                        outcome_col=outcome_col,
                        method=metodo
                    )

                    interpretacion = causal_agent.run(prompt_interpretacion)
                    st.session_state["interpretacion_causalidad"] = interpretacion

                except Exception as e:
                    st.error("❌ Ocurrió un error al estimar o interpretar el efecto causal.")
                    st.exception(e)

        if "interpretacion_causalidad" in st.session_state:
            st.markdown("### 📊 Estimación e interpretación del agente:")
            st.markdown(st.session_state["interpretacion_causalidad"])


    # Paso 7: Validación del estimado (robustez)
    if (
    "causal_model" in st.session_state and 
    "identified_estimand" in st.session_state and 
    "estimate" in st.session_state and 
    "causal_agent" in st.session_state
    ):
        st.subheader("🧪 Validación del estimado (robustez)")

        if st.button("Validar robustez del efecto estimado con el agente"):
            with st.spinner("Evaluando robustez del estimado..."):
                try:
                    prompt = generar_prompt_validacion_robustez()
                    respuesta = st.session_state["causal_agent"].run(prompt)
                    st.session_state["validacion_robustez"] = respuesta

                except Exception as e:
                    st.error("❌ Ocurrió un error al validar el estimado.")
                    st.exception(e)

        if "validacion_robustez" in st.session_state:
            st.markdown("### 🔬 Resultado de la validación del agente:")
            st.markdown(st.session_state["validacion_robustez"])
