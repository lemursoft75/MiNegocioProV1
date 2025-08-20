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
        # Campos de producto y cantidad no son necesarios en Contabilidad si ya se registran en Ventas
        # clave_producto = st.text_input("Clave del producto")
        # cantidad = st.number_input("Cantidad", min_value=0, step=1)
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

            # El campo `Cliente` es crucial para la trazabilidad, así que es buena práctica pedirlo
            # si la categoría es `Cobranza`, `Anticipo Cliente` o `Anticipo Aplicado`.
            cliente_input = ""
            if categoria in ["Cobranza", "Anticipo Cliente", "Anticipo Aplicado"]:
                st.warning("Para esta categoría, es recomendable ingresar un cliente.")
                # Aquí podrías añadir un campo de texto para el cliente

            guardar_transaccion({
                "Fecha": fecha.isoformat(),
                "Clave Producto": "",  # Se deja vacío si no se usa
                "Cantidad": 0,  # Se deja vacío si no se usa
                "Descripción": descripcion,
                "Categoría": categoria,
                "Tipo": tipo,
                "Monto": float(monto),
                "Cliente": ""  # Se deja vacío si no aplica
            })
            st.session_state.reload_transacciones = True
            st.success("✅ Transacción guardada correctamente")
            st.rerun()

    st.divider()
    st.subheader("📋 Histórico contable")

    if st.session_state.transacciones.empty:
        st.info("Aún no hay transacciones registradas.")
        return

    # Usamos el DataFrame completo para el historial
    st.dataframe(st.session_state.transacciones, use_container_width=True)

    st.divider()
    st.subheader("📉 Balance general")

    # --- LÓGICA DE CÁLCULO CORREGIDA ---
    df_transacciones = st.session_state.transacciones.copy()

    # Ingresos son las transacciones de tipo "Ingreso" que NO son de categoría "Cobranza"
    ingresos_brutos = df_transacciones.loc[
        (df_transacciones["Tipo"] == "Ingreso") & (df_transacciones["Categoría"] != "Cobranza"), "Monto"
    ].sum()

    # Los egresos son todos los de tipo "Egreso"
    gastos_totales = df_transacciones.loc[df_transacciones["Tipo"] == "Egreso", "Monto"].sum()

    # El balance neto es el flujo de caja, por lo que incluye todos los ingresos
    ingresos_flujo_caja = df_transacciones.loc[df_transacciones["Tipo"] == "Ingreso", "Monto"].sum()
    balance_flujo_caja = ingresos_flujo_caja - gastos_totales

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Brutos", f"${ingresos_brutos:,.2f}")
    col2.metric("Egresos", f"${gastos_totales:,.2f}")
    col3.metric("Balance Neto (Flujo de Caja)", f"${balance_flujo_caja:,.2f}")

    st.divider()
    st.subheader("📊 Distribución contable")

    # --- GRÁFICO DE PIE CORREGIDO ---
    df_grafico = df_transacciones.copy()
    # Excluir la cobranza del gráfico de pastel para evitar el doble conteo
    df_grafico_filtrado = df_grafico[df_grafico["Categoría"] != "Cobranza"]

    if not df_grafico_filtrado.empty:
        resumen_tipo = df_grafico_filtrado.groupby("Tipo")["Monto"].sum().reset_index()
        fig = px.pie(resumen_tipo, names="Tipo", values="Monto",
                     title="Ingresos Brutos vs Egresos", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos para mostrar en el gráfico (excluyendo la cobranza).")

    st.subheader("📑 Desglose por tipo y categoría")
    if "Categoría" in df_transacciones.columns:
        # Aquí se puede mostrar el desglose COMPLETO para dar la visión detallada de todo,
        # incluyendo la cobranza como una categoría de ingreso.
        resumen_tipo_categoria = (
            df_transacciones
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
        df_transacciones.to_excel(writer, index=False, sheet_name="Transacciones")
    output.seek(0)

    fecha_actual = datetime.date.today().isoformat()
    st.download_button(
        label="📥 Descargar como Excel",
        data=output,
        file_name=f"historial_contable_{fecha_actual}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )