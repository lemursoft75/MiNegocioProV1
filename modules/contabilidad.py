import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime
from utils.db import guardar_transaccion, leer_transacciones, calcular_balance_contable



def render():
    st.title("🧾 Contabilidad")

    # Cargar transacciones desde Firestore
    # Se asegura que las transacciones se recarguen al entrar al módulo
    transacciones_data = leer_transacciones()
    st.session_state.transacciones = pd.DataFrame(transacciones_data)


    # Formulario contable
    with st.form("form_registro"):
        st.subheader("Registrar nueva transacción")
        fecha = st.date_input("Fecha", value=datetime.date.today())
        descripcion = st.text_input("Descripción")
        # Ampliamos las categorías para que coincidan con las posibles del sistema
        categoria = st.selectbox("Categoría", ["Ventas", "Servicios", "Compras", "Sueldos", "Papeleria", "Transporte", "Otro", "Cobranza", "Anticipo Cliente", "Anticipo Aplicado"])
        # --- CAMBIO AQUÍ: "Gasto" por "Egreso" en la UI ---
        tipo = st.radio("Tipo", ["Ingreso", "Egreso"])
        # --- FIN DEL CAMBIO ---
        monto = st.number_input("Monto", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Agregar")

        if submitted:
            transaccion = {
                "Fecha": fecha.isoformat(),
                "Descripción": descripcion,
                "Categoría": categoria,
                "Tipo": tipo, # Esto guardará "Ingreso" o "Egreso" directamente según lo seleccionado en UI
                "Monto": float(monto)
            }
            guardar_transaccion(transaccion)

            # Recargar desde Firestore después de guardar
            st.session_state.transacciones = pd.DataFrame(leer_transacciones())

            st.success("✅ Transacción guardada correctamente")
            st.rerun() # Para refrescar los datos mostrados

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
        # --- CAMBIO AQUÍ: "Gastos" por "Egresos" en la UI ---
        col2.metric("Egresos", f"${gastos:,.2f}")
        # --- FIN DEL CAMBIO ---
        col3.metric("Balance neto", f"${balance:,.2f}")

        st.divider()
        st.subheader("📊 Distribución contable")

        resumen_tipo = st.session_state.transacciones.groupby("Tipo")["Monto"].sum().reset_index()
        fig = px.pie(resumen_tipo, names="Tipo", values="Monto",
                     title="Ingresos vs Egresos", template="plotly_white") # Título actualizado
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