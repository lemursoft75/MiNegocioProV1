# modules/clientes.py
import streamlit as st
import pandas as pd
from utils.db import guardar_cliente, leer_clientes

def render():
    st.title("👥 Gestión de Clientes")

    if "clientes" not in st.session_state:
        clientes_data = leer_clientes()
        st.session_state.clientes = pd.DataFrame(clientes_data)

    with st.form("form_clientes"):
        st.subheader("Agregar nuevo cliente")
        nombre = st.text_input("Nombre")
        correo = st.text_input("Correo")
        telefono = st.text_input("Teléfono")
        empresa = st.text_input("Empresa")
        rfc = st.text_input("RFC")
        submitted = st.form_submit_button("Guardar cliente")

        if submitted:
            nuevo_cliente = {
                "Nombre": nombre,
                "Correo": correo,
                "Teléfono": telefono,
                "Empresa": empresa,
                "RFC": rfc
            }
            guardar_cliente(nuevo_cliente)
            nuevo_df = pd.DataFrame([nuevo_cliente])
            st.session_state.clientes = pd.concat([st.session_state.clientes, nuevo_df], ignore_index=True)
            st.success("✅ Cliente guardado en Firestore y agregado a la lista")

    st.divider()
    st.subheader("📋 Lista de clientes")
    st.dataframe(st.session_state.clientes, use_container_width=True)