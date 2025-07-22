import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime
from PIL import Image
from utils.db import leer_ventas, leer_transacciones, leer_clientes, leer_productos

def render():
    # 🧭 Cabecera tipo ERP con logo local
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        logo = Image.open("assets/logo.png")
        st.image(logo, width=80)
    with col_title:
        st.markdown("## MiNegocio Pro")
        st.caption("By Xibalbá Business Suite")

    st.markdown("### 📊 Panel financiero en tiempo real")

    # 🔄 Cargar datos desde Firestore
    st.session_state.ventas = pd.DataFrame(leer_ventas()) if "ventas" not in st.session_state else st.session_state.ventas
    st.session_state.transacciones = pd.DataFrame(leer_transacciones()) if "transacciones" not in st.session_state else st.session_state.transacciones
    st.session_state.clientes = pd.DataFrame(leer_clientes()) if "clientes" not in st.session_state else st.session_state.clientes
    st.session_state.productos = pd.DataFrame(leer_productos()) if "productos" not in st.session_state else st.session_state.productos

    ventas_df = st.session_state.ventas
    transacciones_df = st.session_state.transacciones
    clientes_df = st.session_state.clientes
    productos_df = st.session_state.productos

    # ✅ Asegurar que 'Monto' esté presente
    if "Monto" not in transacciones_df.columns:
        transacciones_df["Monto"] = 0
    else:
        transacciones_df["Monto"] = pd.to_numeric(transacciones_df["Monto"], errors="coerce").fillna(0)

    ingresos = ventas_df["Total"].sum() if "Total" in ventas_df.columns and not ventas_df.empty else 0
    gastos = transacciones_df.query("Tipo == 'Gasto'")["Monto"].sum() if not transacciones_df.empty else 0
    balance = ingresos - gastos
    delta_pct = f"{(balance / ingresos * 100):.1f}%" if ingresos else "0%"

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos del mes", f"${ingresos:,.0f}", "+5%" if ingresos else "0%")
    col2.metric("Gastos del mes", f"${gastos:,.0f}", "-2%" if gastos else "0%")
    col3.metric("Balance neto", f"${balance:,.0f}", delta_pct)

    st.divider()
    st.markdown("### 📈 Composición financiera")
    df_bar = pd.DataFrame({
        "Categoría": ["Ventas", "Gastos", "Ganancia"],
        "Monto": [ingresos, gastos, balance]
    })
    st.plotly_chart(px.bar(df_bar, x="Categoría", y="Monto", color="Categoría",
                           template="plotly_white", title="Distribución por tipo"),
                    use_container_width=True)

    st.divider()
    st.markdown("### 🧩 Indicadores administrativos")
    col4, col5 = st.columns(2)
    with col4:
        st.metric("Clientes registrados", len(clientes_df))
        st.metric("Productos activos", len(productos_df))
    with col5:
        st.write("#### Flujo de ventas por día")
        if not ventas_df.empty and "Fecha" in ventas_df.columns:
            flujo = ventas_df.groupby("Fecha")["Total"].sum().reset_index()
            st.plotly_chart(px.line(flujo, x="Fecha", y="Total", markers=True,
                                    template="plotly_white", title="Ingresos diarios"),
                            use_container_width=True)
        else:
            st.info("No hay ventas registradas aún para mostrar el flujo diario.")

    st.divider()
    st.markdown("### 🧮 Análisis por cliente y producto")
    if not ventas_df.empty:
        resumen_clientes = ventas_df.groupby("Cliente")["Total"].sum().reset_index()
        st.subheader("💼 Ventas por cliente")
        st.dataframe(resumen_clientes, use_container_width=True)
        st.plotly_chart(px.bar(resumen_clientes, x="Cliente", y="Total",
                               title="Ingresos por cliente", template="plotly_white"),
                        use_container_width=True)

        resumen_productos = ventas_df.groupby("Producto")["Cantidad"].sum().reset_index()
        st.subheader("📦 Productos más vendidos")
        st.dataframe(resumen_productos, use_container_width=True)
        st.plotly_chart(px.bar(resumen_productos, x="Producto", y="Cantidad",
                               title="Ranking de productos", template="plotly_white"),
                        use_container_width=True)
    else:
        resumen_clientes = pd.DataFrame()
        resumen_productos = pd.DataFrame()

    if "Costo Unitario" in productos_df.columns:
        st.divider()
        st.subheader("📊 Margen por producto")
        margen_df = productos_df[["Nombre", "Precio Unitario", "Costo Unitario"]].copy()
        margen_df["Margen"] = margen_df["Precio Unitario"] - productos_df["Costo Unitario"]
        st.dataframe(margen_df, use_container_width=True)
    else:
        margen_df = pd.DataFrame()

    st.divider()
    st.subheader("📤 Exportar resumen")

    resumen = {
        "Resumen financiero": df_bar,
        "Ventas por cliente": resumen_clientes,
        "Productos más vendidos": resumen_productos,
        "Margen por producto": margen_df
    }

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for nombre, df in resumen.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=nombre[:31], index=False)
    output.seek(0)

    fecha_actual = datetime.date.today().isoformat()
    st.download_button(
        label="📥 Descargar resumen Excel",
        data=output,
        file_name=f"resumen_financiero_{fecha_actual}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 🎨 Estilo visual
    st.markdown("""
        <style>
        .block-container { padding: 2rem; }
        h1 { font-family: 'Segoe UI', sans-serif; color: #1F4E79; }
        .stMetricLabel { font-size: 16px !important; }
        .stMetricValue { font-size: 22px !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)