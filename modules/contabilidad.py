import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime
from utils.db import guardar_transaccion, leer_transacciones, calcular_balance_contable

def render():
    st.title("🧾 Contabilidad")

    # Cargar transacciones desde Firestore
    def render():
        st.title("🧾 Contabilidad")

        # Cargar transacciones desde Firestore
        if "transacciones" not in st.session_state:
            transacciones_data = leer_transacciones()
            transacciones = pd.DataFrame(transacciones_data)
            st.session_state.transacciones = transacciones

            # Debug visual (opcional, puede comentarse luego)
            st.write("Transacciones cargadas:", transacciones.head())
            st.write("Columnas:", transacciones.columns.tolist())

    # Formulario contable
    with st.form("form_registro"):
        st.subheader("Registrar nueva transacción")
        fecha = st.date_input("Fecha", value=datetime.date.today())
        descripcion = st.text_input("Descripción")
        categoria = st.selectbox("Categoría", ["Ventas", "Servicios", "Compras", "Sueldos", "Otro"])
        tipo = st.radio("Tipo", ["Ingreso", "Gasto"])
        monto = st.number_input("Monto", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Agregar")

        if submitted:
            transaccion = {
                "Fecha": fecha.isoformat(),
                "Descripción": descripcion,
                "Categoría": categoria,
                "Tipo": tipo,
                "Monto": float(monto)
            }
            guardar_transaccion(transaccion)

            # Recargar desde Firestore después de guardar
            transacciones_actualizadas = leer_transacciones()
            st.session_state.transacciones = pd.DataFrame(transacciones_actualizadas)

            st.success("✅ Transacción guardada correctamente")

    st.divider()
    st.subheader("📋 Histórico contable")

    if st.session_state.transacciones.empty:
        st.info("Aún no hay transacciones registradas.")
    else:
        st.dataframe(st.session_state.transacciones, use_container_width=True)

        st.divider()
        st.subheader("📉 Balance general")

        ingresos, gastos, balance = calcular_balance_contable()
        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos", f"${ingresos:,.2f}")
        col2.metric("Gastos", f"${gastos:,.2f}")
        col3.metric("Balance neto", f"${balance:,.2f}")

        st.divider()
        st.subheader("📊 Distribución contable")

        resumen_tipo = st.session_state.transacciones.groupby("Tipo")["Monto"].sum().reset_index()
        fig = px.pie(resumen_tipo, names="Tipo", values="Monto",
                     title="Ingresos vs Gastos", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

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