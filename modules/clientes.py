import streamlit as st
import pandas as pd
import io
from utils.db import guardar_cliente, leer_clientes, actualizar_cliente

# --- Cachear la lectura de clientes para evitar múltiples llamadas ---
@st.cache_data(ttl=60)  # cache 1 minuto
def get_clientes():
    return pd.DataFrame(leer_clientes())

# Helper para convertir DataFrame a Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes')
    return output.getvalue()

def render():
    st.title("👥 Gestión de Clientes")

    # Cargar clientes (cacheado)
    if "clientes" not in st.session_state:
        st.session_state.clientes = get_clientes()
    else:
        # Evitar que se pierdan los cambios tras agregar o editar
        if st.session_state.get("reload_clientes", False):
            st.session_state.clientes = get_clientes()
            st.session_state.reload_clientes = False

    # --- Formulario agregar cliente ---
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
            elif id_cliente in st.session_state.clientes["ID"].astype(str).values:
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
                st.session_state.reload_clientes = True
                st.success("✅ Cliente guardado correctamente")
                st.rerun()

    st.divider()

    # --- Formulario editar cliente ---
    st.subheader("✏️ Editar cliente existente")
    if not st.session_state.clientes.empty:
        clientes_df = st.session_state.clientes.copy()
        clientes_df["ID-Nombre"] = clientes_df["ID"].astype(str) + " - " + clientes_df["Nombre"].astype(str)

        seleccion = st.selectbox(
            "Selecciona un cliente para editar",
            clientes_df["ID-Nombre"].tolist(),
            key="select_cliente_edit"
        )
        id_seleccionado = seleccion.split(" - ")[0]

        cliente_original = clientes_df[clientes_df["ID"].astype(str) == id_seleccionado].iloc[0]

        with st.form("form_editar_cliente"):
            nombre_edit = st.text_input("Nombre", value=cliente_original["Nombre"], key="edit_nombre")
            correo_edit = st.text_input("Correo", value=cliente_original["Correo"], key="edit_correo")
            telefono_edit = st.text_input("Teléfono", value=cliente_original["Teléfono"], key="edit_telefono")
            empresa_edit = st.text_input("Empresa", value=cliente_original["Empresa"], key="edit_empresa")
            rfc_edit = st.text_input("RFC", value=cliente_original["RFC"], key="edit_rfc")
            limite_credito_edit = st.number_input(
                "💳 Límite de crédito autorizado",
                min_value=0.0,
                value=float(cliente_original["Límite de crédito"]),
                step=100.0,
                format="%.2f",
                key="edit_limite_credito"
            )

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
                st.session_state.reload_clientes = True
                st.success("✅ Cliente actualizado correctamente")
                st.rerun()
    else:
        st.info("No hay clientes para editar.")

    st.divider()

    # --- Lista de clientes ---
    st.subheader("📋 Lista de clientes")
    df_to_display = st.session_state.clientes.copy()
    if "ID-Nombre" in df_to_display.columns:
        df_to_display.drop(columns=["ID-Nombre"], inplace=True)

    st.dataframe(df_to_display, use_container_width=True)

    # --- Exportar a Excel ---
    if not df_to_display.empty:
        st.download_button(
            label="Exportar lista de clientes a Excel",
            data=to_excel(df_to_display),
            file_name="lista_clientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay clientes para exportar.")
