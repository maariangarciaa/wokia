import os
import pandas as pd
from auto_doc.services.datasets import (
    DATASETS_DIR,
    list_datasets,
    load_dataset,
    save_dataset_bytes,
)

BASE_DIR = DATASETS_DIR
BASE_DIR.mkdir(parents=True, exist_ok=True) 

def extract_filename(file_path):
    """Obtiene el nombre del archivo sin extensión."""
    file_name, _ = os.path.splitext(os.path.basename(file_path))
    return file_name

def encode_file_name(name: str) -> str:
    """Codifica el nombre del proyecto para evitar espacios o caracteres problemáticos."""
    return name.lower().replace(" ", "_")

def save_uploaded_file(uploaded_file):
    """Guarda el archivo en 'auto_doc/files/' y devuelve la ruta."""
    return save_dataset_bytes(uploaded_file.name, uploaded_file.getbuffer())


def load_file(file_path: str) -> pd.DataFrame:
    """
    Carga archivos en formato CSV o Excel (XLSX) y devuelve un DataFrame con un máximo de filas y columnas.

    Parámetros:
    - file_path (str): Ruta del archivo.
    - max_rows (int): Número máximo de filas a cargar. Por defecto 200.
    - max_columns (int): Número máximo de columnas a cargar. Por defecto 10.

    Retorna:
    - pd.DataFrame: Contenido del archivo como DataFrame.
    """
    return load_dataset(file_path)

def list_all_datasets():
    """
    Lista todos los archivos disponibles en auto_doc/files/ con extensiones .csv o .xlsx.
    Retorna una lista de diccionarios con nombre y ruta.
    """
    return list_datasets(BASE_DIR)

import streamlit as st

def mostrar_respuesta_agente(clave, respuesta=None):
    """
    Muestra la respuesta del agente desde session_state si existe,
    o guarda una nueva si se proporciona. No muestra título.

    Parámetros:
    - clave (str): nombre de la variable en session_state donde se almacena la respuesta.
    - respuesta (str): contenido nuevo para guardar (opcional).
    """
    if respuesta is not None:
        st.session_state[clave] = respuesta

    if clave in st.session_state:
        st.markdown(st.session_state[clave])

