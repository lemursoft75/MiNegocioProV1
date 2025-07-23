import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime
from PIL import Image
from utils.db import leer_ventas, leer_transacciones, leer_clientes, leer_productos, calcular_balance_contable # Importar calcular_balance_contable

from dotenv import load_dotenv
load_dotenv()  # <-- ¡Carga .env antes de importar módulos que dependen de variables de entorno!

def render():
    # 🧭 Cabecera tipo ERP con logo local
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        # Asegúrate de que 'assets/logo.png' exista en tu proyecto
        try:
            logo = Image.open("assets/logo.png")
            st.image(logo, width=80)
        except FileNotFoundError:
            st.warning("Logo no encontrado en 'assets/logo.png'. Asegúrate de que la ruta es correcta.")
            st.image("https://via.placeholder.com/80", width=80) # Placeholder si no se encuentra el logo
    with col_title:
        st.markdown("## MiNegocio Pro")
        st.caption("By Xibalbá Business Suite")

    st.markdown("### 📊 Panel financiero en tiempo real")

    # 🔄 Cargar datos desde Firestore
    # Siempre recargamos los datos para asegurar que el dashboard esté actualizado
    # Esto también recargará los DataFrames de st.session_state automáticamente.
    st.session_state.ventas = leer_ventas()
    st.session_state.transacciones = leer_transacciones()
    st.session_state.clientes = leer_clientes()
    st.session_state.productos = leer_productos()

    ventas_df = st.session_state.ventas
    transacciones_df = st.session_state.transacciones
    clientes_df = st.session_state.clientes
    productos_df = st.session_state.productos

    # ✅ Asegurar que 'Monto' en transacciones_df sea numérico
    if "Monto" not in transacciones_df.columns:
        transacciones_df["Monto"] = 0.0 # Asegurar que sea float
    else:
        transacciones_df["Monto"] = pd.to_numeric(transacciones_df["Monto"], errors="coerce").fillna(0.0)

    # ✅ Asegurar que 'Total' en ventas_df sea numérico
    if "Total" not in ventas_df.columns:
        ventas_df["Total"] = 0.0
    else:
        ventas_df["Total"] = pd.to_numeric(ventas_df["Total"], errors="coerce").fillna(0.0)

    # 🚀 Cálculo de Ingresos y Egresos
    # Usaremos la función calcular_balance_contable de utils.db para consistencia
    ingresos_totales, egresos_totales, balance_neto = calcular_balance_contable()

    # Los "ingresos del mes" y "gastos del mes" en las métricas pueden ser filtrados por fecha si quieres.
    # Por ahora, usaré los totales anuales de calcular_balance_contable para estas métricas,
    # que es lo que la función ya proporciona (suma de todos los tiempos).
    # Si quisieras "del mes", necesitarías filtrar por fecha actual en las funciones leer_X o aquí.

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Totales", f"${ingresos_totales:,.0f}") # Ajustado a "Totales"
    col2.metric("Egresos Totales", f"${egresos_totales:,.0f}") # ¡CAMBIO CLAVE AQUÍ: 'Egresos' en lugar de 'Gastos'
    col3.metric("Balance Neto", f"${balance_neto:,.0f}")

    st.divider()
    st.markdown("### 📈 Composición financiera")
    # Para el gráfico de barras, usamos los mismos valores
    df_bar = pd.DataFrame({
        "Categoría": ["Ingresos", "Egresos", "Balance Neto"], # ¡CAMBIO CLAVE AQUÍ: 'Egresos'
        "Monto": [ingresos_totales, egresos_totales, balance_neto]
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
            # Convertir la columna Fecha a datetime para asegurar un orden correcto
            ventas_df['Fecha'] = pd.to_datetime(ventas_df['Fecha'])
            flujo = ventas_df.groupby("Fecha")["Total"].sum().reset_index()
            # Ordenar por fecha para el gráfico de línea
            flujo = flujo.sort_values(by="Fecha")
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
                # Asegurarse de que el nombre de la hoja no exceda 31 caracteres
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

    # 🎨 Estilo visual
    st.markdown("""
        <style>
        .block-container { padding: 2rem; }
        h1 { font-family: 'Segoe UI', sans-serif; color: #1F4E79; }
        .stMetricLabel { font-size: 16px !important; }
        .stMetricValue { font-size: 22px !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)