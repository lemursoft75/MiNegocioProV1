import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime
from PIL import Image
from utils.db import leer_ventas, leer_transacciones, leer_clientes, leer_productos, calcular_balance_contable
from dotenv import load_dotenv

load_dotenv()

# ---- Funciones cacheadas ----
@st.cache_data(ttl=60)
def get_ventas():
    return pd.DataFrame(leer_ventas())

@st.cache_data(ttl=60)
def get_transacciones():
    df = pd.DataFrame(leer_transacciones())
    if "Monto" in df.columns:
        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
    return df

@st.cache_data(ttl=60)
def get_clientes():
    return pd.DataFrame(leer_clientes())

@st.cache_data(ttl=60)
def get_productos():
    return pd.DataFrame(leer_productos())

def render():
    # ✅ Verificar sesión antes de continuar
    if "uid" not in st.session_state:
        st.warning("⚠️ Debes iniciar sesión para ver el panel.")
        st.stop()

    # 🧭 Cabecera tipo ERP con logo local
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        try:
            logo = Image.open("assets/logo.png")
            st.image(logo, width=80)
        except FileNotFoundError:
            st.warning("Logo no encontrado en 'assets/logo.png'.")
            st.image("https://via.placeholder.com/80", width=80)
    with col_title:
        st.markdown("## MiNegocio Pro")
        st.caption("By Xibalbá Business Suite")

    st.markdown("### 📊 Panel financiero en tiempo real")

    # 🔄 Cargar datos solo si no están o si hay reload
    if "ventas" not in st.session_state or st.session_state.get("reload_ventas", False):
        st.session_state.ventas = get_ventas()
        st.session_state.reload_ventas = False

    if "transacciones" not in st.session_state or st.session_state.get("reload_transacciones", False):
        st.session_state.transacciones = get_transacciones()
        st.session_state.reload_transacciones = False

    if "clientes" not in st.session_state or st.session_state.get("reload_clientes", False):
        st.session_state.clientes = get_clientes()
        st.session_state.reload_clientes = False

    if "productos" not in st.session_state or st.session_state.get("reload_productos", False):
        st.session_state.productos = get_productos()
        st.session_state.reload_productos = False

    ventas_df = st.session_state.ventas
    transacciones_df = st.session_state.transacciones
    clientes_df = st.session_state.clientes
    productos_df = st.session_state.productos

    # ✅ Asegurar numéricos
    if "Total" not in ventas_df.columns:
        ventas_df["Total"] = 0.0
    else:
        ventas_df["Total"] = pd.to_numeric(ventas_df["Total"], errors="coerce").fillna(0.0)

    # 🚀 Cálculo de Ingresos y Egresos
    ingresos_totales, egresos_totales, balance_neto = calcular_balance_contable()

    # ✅ Cálculo de ingresos reales (ventas al contado + cobranza)
    ventas_contado = ventas_df["Monto Contado"].sum() if "Monto Contado" in ventas_df.columns else 0.0
    cobranza_credito = 0.0
    if not transacciones_df.empty and "Categoría" in transacciones_df.columns:
        cobranza_credito = transacciones_df[
            transacciones_df["Categoría"] == "Cobranza"
        ]["Monto"].sum()
    ingresos_reales = ventas_contado + cobranza_credito

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos Totales", f"${ingresos_totales:,.0f}")
    col2.metric("Egresos Totales", f"${egresos_totales:,.0f}")
    col3.metric("Balance Neto", f"${balance_neto:,.0f}")
    col4.metric("Ingresos Reales", f"${ingresos_reales:,.0f}")

    st.divider()
    st.markdown("### 📈 Composición financiera")
    df_bar = pd.DataFrame({
        "Categoría": ["Ingresos", "Egresos", "Balance Neto", "Ingresos Reales"],
        "Monto": [ingresos_totales, egresos_totales, balance_neto, ingresos_reales]
    })
    st.plotly_chart(px.bar(df_bar, x="Categoría", y="Monto", color="Categoría",
                           template="plotly_white", title="Distribución por tipo"),
                    use_container_width=True)

    st.divider()
    st.markdown("### 📑 Desglose por tipo y categoría")
    if not transacciones_df.empty and "Categoría" in transacciones_df.columns:
        resumen_tipo_categoria = (
            transacciones_df
            .groupby(["Tipo", "Categoría"])["Monto"]
            .sum()
            .reset_index()
            .sort_values(by="Monto", ascending=False)
        )
        st.dataframe(resumen_tipo_categoria, use_container_width=True)
        fig_tc = px.bar(
            resumen_tipo_categoria,
            x="Monto",
            y="Categoría",
            color="Tipo",
            barmode="group",
            title="Importe por categoría y tipo",
            template="plotly_white",
            text_auto=".2s",
            orientation="h"
        )
        st.plotly_chart(fig_tc, use_container_width=True)
    else:
        st.info("No hay datos de transacciones para mostrar el desglose por categoría.")

    st.divider()
    st.markdown("### 🧩 Indicadores administrativos")
    col4, col5 = st.columns(2)
    with col4:
        st.metric("Clientes registrados", len(clientes_df))
        st.metric("Productos activos", len(productos_df))
    with col5:
        st.write("#### Flujo de ventas por día")
        if not ventas_df.empty and "Fecha" in ventas_df.columns:
            ventas_df['Fecha'] = pd.to_datetime(ventas_df['Fecha'])
            flujo = ventas_df.groupby("Fecha")["Total"].sum().reset_index().sort_values(by="Fecha")
            st.plotly_chart(px.line(flujo, x="Fecha", y="Total", markers=True,
                                    template="plotly_white", title="Ingresos diarios por ventas"),
                            use_container_width=True)
        else:
            st.info("No hay ventas registradas aún para mostrar el flujo diario.")

    st.divider()
    st.markdown("### 📊 Análisis por cliente y producto")
    if not ventas_df.empty:
        resumen_clientes = ventas_df.groupby("Cliente")["Total"].sum().reset_index().sort_values(by="Total", ascending=False)
        st.subheader("💼 Ventas por cliente")
        st.dataframe(resumen_clientes, use_container_width=True)
        st.plotly_chart(px.bar(resumen_clientes, x="Cliente", y="Total",
                               title="Ingresos por cliente", template="plotly_white"),
                        use_container_width=True)

        resumen_productos = ventas_df.groupby("Producto")["Cantidad"].sum().reset_index().sort_values(by="Cantidad", ascending=False)
        st.subheader("📦 Productos más vendidos (por cantidad)")
        st.dataframe(resumen_productos, use_container_width=True)
        st.plotly_chart(px.bar(resumen_productos, x="Producto", y="Cantidad",
                               title="Ranking de productos", template="plotly_white"),
                        use_container_width=True)
    else:
        st.info("No hay datos de ventas para mostrar análisis por cliente y producto.")
        resumen_clientes = pd.DataFrame()
        resumen_productos = pd.DataFrame()

    if "Costo Unitario" in productos_df.columns and "Precio Unitario" in productos_df.columns:
        st.divider()
        st.subheader("📊 Margen por producto (Unitario)")
        margen_df = productos_df[["Nombre", "Precio Unitario", "Costo Unitario"]].copy()
        margen_df["Margen Unitario"] = margen_df["Precio Unitario"] - margen_df["Costo Unitario"]
        st.dataframe(margen_df.sort_values(by="Margen Unitario", ascending=False), use_container_width=True)
    else:
        st.info("No hay datos completos de costo unitario o precio unitario para calcular el margen.")
        margen_df = pd.DataFrame()

    st.divider()
    st.subheader("📤 Exportar resumen")
    resumen_para_exportar = {
        "Resumen Financiero": df_bar,
        "Ventas por Cliente": resumen_clientes,
        "Productos Mas Vendidos": resumen_productos,
        "Margen por Producto": margen_df
    }
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for nombre, df in resumen_para_exportar.items():
            if not df.empty:
                sheet_name = nombre.replace(" ", "_")[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)

    fecha_actual = datetime.date.today().isoformat()
    st.download_button(
        label="📥 Descargar resumen Excel",
        data=output,
        file_name=f"resumen_financiero_{fecha_actual}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("""
        <style>
        .block-container { padding: 2rem; }
        h1 { font-family: 'Segoe UI', sans-serif; color: #1F4E79; }
        .stMetricLabel { font-size: 16px !important; }
        .stMetricValue { font-size: 22px !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
