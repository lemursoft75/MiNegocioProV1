import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime
from utils.db import guardar_transaccion, leer_transacciones

# --- Cachear transacciones ---
@st.cache_data(ttl=60)
def get_transacciones():
    df = pd.DataFrame(leer_transacciones())
    if "Monto" in df.columns:
        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
    return df

def calcular_balance_local(df):
    ingresos = df.loc[df["Tipo"] == "Ingreso", "Monto"].sum()
    gastos = df.loc[df["Tipo"] == "Egreso", "Monto"].sum()
    return ingresos, gastos, ingresos - gastos

def render():
    if "uid" not in st.session_state:
        st.warning("⚠️ Debes iniciar sesión para ver Contabilidad.")
        st.stop()

    st.title("🧾 Contabilidad")

    # Cargar transacciones
    if "transacciones" not in st.session_state:
        st.session_state.transacciones = get_transacciones()
    elif st.session_state.get("reload_transacciones", False):
        st.session_state.transacciones = get_transacciones()
        st.session_state.reload_transacciones = False

    # --- Formulario para nueva transacción ---
    with st.form("form_registro"):
        st.subheader("Registrar nueva transacción")
        fecha = st.date_input("Fecha", value=datetime.date.today())
        clave_producto = st.text_input("Clave del producto")  # NUEVO
        cantidad = st.number_input("Cantidad", min_value=0, step=1)  # NUEVO
        descripcion = st.text_input("Descripción")
        categoria = st.selectbox(
            "Categoría",
            ["Ventas", "Servicios", "Compras", "Sueldos", "Papeleria",
             "Transporte", "Otro", "Cobranza", "Anticipo Cliente", "Anticipo Aplicado"]
        )
        tipo = st.radio("Tipo", ["Ingreso", "Egreso"])
        monto = st.number_input("Monto", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Agregar")

        if submitted:
            if "uid" not in st.session_state:
                st.error("Tu sesión expiró. Inicia sesión de nuevo.")
                st.stop()

            guardar_transaccion({
                "Fecha": fecha.isoformat(),
                "Clave Producto": clave_producto,  # NUEVO
                "Cantidad": cantidad,  # NUEVO
                "Descripción": descripcion,
                "Categoría": categoria,
                "Tipo": tipo,
                "Monto": float(monto)
            })
            st.session_state.reload_transacciones = True
            st.success("✅ Transacción guardada correctamente")
            st.rerun()

    st.divider()
    st.subheader("📋 Histórico contable")

    if st.session_state.transacciones.empty:
        st.info("Aún no hay transacciones registradas.")
        return

    # Mostrar todas las columnas (incluyendo Clave y Cantidad)
    st.dataframe(st.session_state.transacciones, use_container_width=True)

    st.divider()
    st.subheader("📉 Balance general")

    ingresos, gastos, balance = calcular_balance_local(st.session_state.transacciones)
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos", f"${ingresos:,.2f}")
    col2.metric("Egresos", f"${gastos:,.2f}")
    col3.metric("Balance neto", f"${balance:,.2f}")

    st.divider()
    st.subheader("📊 Distribución contable")

    resumen_tipo = st.session_state.transacciones.groupby("Tipo")["Monto"].sum().reset_index()
    fig = px.pie(resumen_tipo, names="Tipo", values="Monto",
                 title="Ingresos vs Egresos", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📑 Desglose por tipo y categoría")
    if "Categoría" in st.session_state.transacciones.columns:
        resumen_tipo_categoria = (
            st.session_state.transacciones
            .groupby(["Tipo", "Categoría"])["Monto"]
            .sum()
            .reset_index()
            .sort_values(by="Monto", ascending=False)
        )
        st.dataframe(resumen_tipo_categoria, use_container_width=True)

        fig_tc = px.bar(
            resumen_tipo_categoria,
            x="Categoría",
            y="Monto",
            color="Tipo",
            barmode="group",
            title="Importe por categoría y tipo",
            template="plotly_white",
            text_auto=".2s"
        )
        st.plotly_chart(fig_tc, use_container_width=True)

    st.subheader("📤 Exportar historial contable")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        st.session_state.transacciones.to_excel(writer, index=False, sheet_name="Transacciones")
    output.seek(0)

    fecha_actual = datetime.date.today().isoformat()
    st.download_button(
        label="📥 Descargar como Excel",
        data=output,
        file_name=f"historial_contable_{fecha_actual}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
