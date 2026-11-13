import streamlit as st
from auto_doc.services.datasets import list_datasets, save_dataset_bytes

def mostrar_subida_archivo():
    with st.container():
        st.markdown(
            """
            <div class="page-kicker">Datos</div>
            <h1 class="page-title">Prepara tu dataset</h1>
            <p class="page-subtitle">Selecciona un archivo existente o sube un CSV/Excel para iniciar la exploracion.</p>
            """,
            unsafe_allow_html=True,
        )

        # Mostrar archivos previos si existen
        datasets = list_datasets()
        if datasets:
            opciones = [d["file_name"] for d in datasets]
            seleccion = st.selectbox(
                "Selecciona un archivo previamente subido (opcional)",
                ["Elige un archivo..."] + opciones
            )

            if seleccion != "Elige un archivo...":
                seleccionado = next(d for d in datasets if d["file_name"] == seleccion)
                st.success(f"Archivo seleccionado: `{seleccionado['file_name']}`")
                st.session_state["file_path"] = seleccionado["file_path"]
                return

        # Subida nueva
        archivo = st.file_uploader("Sube tu archivo CSV o Excel", type=["csv", "xlsx"])

        if st.button("Siguiente"):
            if not archivo:
                st.error("Por favor, sube un archivo antes de continuar.")
                return

            file_path = save_dataset_bytes(archivo.name, archivo.getbuffer())
            st.session_state["file_path"] = str(file_path)

            st.success("Archivo subido con exito. Puedes continuar.")
