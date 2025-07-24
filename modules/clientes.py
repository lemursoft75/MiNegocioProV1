import streamlit as st
import pandas as pd
from utils.db import guardar_cliente, leer_clientes, actualizar_cliente


def render():
    st.title("👥 Gestión de Clientes")

    if "clientes" not in st.session_state:
        clientes_data = leer_clientes()
        st.session_state.clientes = pd.DataFrame(clientes_data)

    with st.form("form_clientes"):
        st.subheader("➕ Agregar nuevo cliente")
        id_cliente = st.text_input("🆔 Clave única del cliente (ID)", max_chars=20)
        nombre = st.text_input("Nombre")
        correo = st.text_input("Correo")
        telefono = st.text_input("Teléfono")
        empresa = st.text_input("Empresa")
        rfc = st.text_input("RFC")
        limite_credito = st.number_input("💳 Límite de crédito autorizado", min_value=0.0, step=100.0, format="%.2f")

        submitted = st.form_submit_button("Guardar cliente")

        if submitted:
            if not id_cliente:
                st.error("⚠️ Debes ingresar una clave única para el cliente.")
            elif id_cliente in st.session_state.clientes["ID"].values:
                st.error("❌ Ya existe un cliente con esa clave única. Usa otra.")
            else:
                nuevo_cliente = {
                    "ID": id_cliente,
                    "Nombre": nombre,
                    "Correo": correo,
                    "Teléfono": telefono,
                    "Empresa": empresa,
                    "RFC": rfc,
                    "Límite de crédito": limite_credito
                }
                guardar_cliente(id_cliente, nuevo_cliente)
                nuevo_df = pd.DataFrame([nuevo_cliente])
                st.session_state.clientes = pd.concat([st.session_state.clientes, nuevo_df], ignore_index=True)
                st.success("✅ Cliente guardado correctamente")

    st.divider()

    st.subheader("✏️ Editar cliente existente")
    if not st.session_state.clientes.empty:
        st.session_state.clientes["ID-Nombre"] = st.session_state.clientes["ID"] + " - " + st.session_state.clientes[
            "Nombre"]
        seleccion = st.selectbox("Selecciona un cliente para editar", st.session_state.clientes["ID-Nombre"].tolist())
        id_seleccionado = seleccion.split(" - ")[0]

        cliente_original = st.session_state.clientes[st.session_state.clientes["ID"] == id_seleccionado].iloc[0]

        with st.form("form_editar_cliente"):
            nombre_edit = st.text_input("Nombre", value=cliente_original["Nombre"])
            correo_edit = st.text_input("Correo", value=cliente_original["Correo"])
            telefono_edit = st.text_input("Teléfono", value=cliente_original["Teléfono"])
            empresa_edit = st.text_input("Empresa", value=cliente_original["Empresa"])
            rfc_edit = st.text_input("RFC", value=cliente_original["RFC"])
            limite_credito_edit = st.number_input("💳 Límite de crédito autorizado", min_value=0.0,
                                                  value=cliente_original["Límite de crédito"], step=100.0,
                                                  format="%.2f")

            actualizar = st.form_submit_button("Actualizar cliente")

            if actualizar:
                cliente_actualizado = {
                    "ID": id_seleccionado,
                    "Nombre": nombre_edit,
                    "Correo": correo_edit,
                    "Teléfono": telefono_edit,
                    "Empresa": empresa_edit,
                    "RFC": rfc_edit,
                    "Límite de crédito": limite_credito_edit
                }
                actualizar_cliente(id_seleccionado, cliente_actualizado)
                for clave, valor in cliente_actualizado.items():
                    st.session_state.clientes.loc[
                        st.session_state.clientes["ID"] == id_seleccionado, clave
                    ] = valor

                st.success("✅ Cliente actualizado correctamente")

    st.divider()
    st.subheader("📋 Lista de clientes")
    st.dataframe(st.session_state.clientes, use_container_width=True)
