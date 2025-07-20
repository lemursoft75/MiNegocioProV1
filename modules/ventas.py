import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import guardar_venta, leer_ventas

def render():
    st.title("💸 Ventas")

    # Validar existencia de datos
    if "clientes" not in st.session_state or st.session_state.clientes.empty:
        st.warning("⚠️ No hay clientes registrados. Agrega alguno en 'Clientes'.")
        st.stop()

    if "productos" not in st.session_state or st.session_state.productos.empty:
        st.warning("⚠️ No hay productos registrados. Agrega uno en 'Productos'.")
        st.stop()

    # Cargar ventas desde Firestore si no están
    if "ventas" not in st.session_state:
        ventas_data = leer_ventas()
        st.session_state.ventas = pd.DataFrame(ventas_data)

    with st.form("form_ventas"):
        st.subheader("Registrar nueva venta")
        fecha = st.date_input("Fecha")
        cliente = st.selectbox("Cliente", st.session_state.clientes["Nombre"])
        producto = st.selectbox("Producto/Servicio", st.session_state.productos["Nombre"])
        cantidad = st.number_input("Cantidad", min_value=1)

        # Obtener precio unitario
        precio = st.session_state.productos.loc[
            st.session_state.productos["Nombre"] == producto, "Precio Unitario"
        ].values[0]

        total = cantidad * precio
        metodo_pago = st.selectbox("Método de pago", ["Efectivo", "Transferencia", "Tarjeta"])
        tipo_venta = st.selectbox("Tipo de venta", ["Contado", "Crédito"])
        st.markdown(f"**Precio unitario:** ${precio:.2f}")
        st.markdown(f"**Total:** ${total:.2f}")
        submitted = st.form_submit_button("Registrar venta")

        if submitted:
            venta_dict = {
                "Fecha": fecha.isoformat(),
                "Cliente": cliente,
                "Producto": producto,
                "Cantidad": cantidad,
                "Precio Unitario": precio,
                "Total": total,
                "Método de pago": metodo_pago,
                "Tipo de venta": tipo_venta  # ⬅️ nuevo campo aquí
            }
            guardar_venta(venta_dict)  # Guarda en Firestore + ingreso contable
            nueva = pd.DataFrame([venta_dict])
            st.session_state.ventas = pd.concat([st.session_state.ventas, nueva], ignore_index=True)
            st.success("✅ Venta registrada correctamente")

    st.divider()
    st.subheader("📋 Histórico de ventas")
    st.dataframe(st.session_state.ventas, use_container_width=True)

    if not st.session_state.ventas.empty:
        st.subheader("📊 Ingresos diarios")
        df_daily = st.session_state.ventas.groupby("Fecha")["Total"].sum().reset_index()
        fig = px.bar(df_daily, x="Fecha", y="Total", title="Ventas por día", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)