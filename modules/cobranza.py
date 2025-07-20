import streamlit as st
import pandas as pd
from utils.db import leer_ventas, guardar_transaccion, leer_transacciones

def render():
    st.title("💰 Módulo de cobranza")

    ventas = pd.DataFrame(leer_ventas())
    transacciones = pd.DataFrame(leer_transacciones())

    st.write("📦 Ventas cargadas:", ventas[["Cliente", "Tipo de venta", "Método de pago", "Total"]])

    # ⚙️ Filtrar ventas a crédito
    ventas["Tipo de venta"] = ventas["Tipo de venta"].astype(str)
    creditos = ventas[ventas["Tipo de venta"] == "Crédito"]

    if creditos.empty:
        st.info("No hay ventas a crédito registradas.")
        st.stop()

    # 📊 Calcular saldos por cliente
    deuda_total = creditos.groupby("Cliente")["Total"].sum().reset_index()

    pagos_cobranza = transacciones[
        transacciones["Categoría"].astype(str) == "Cobranza"
    ] if not transacciones.empty else pd.DataFrame()

    if not pagos_cobranza.empty and "Cliente" in pagos_cobranza.columns:
        pagos_total = pagos_cobranza.groupby("Cliente")["Monto"].sum().reset_index()
    else:
        pagos_total = pd.DataFrame(columns=["Cliente", "Monto"])

    saldos = deuda_total.merge(pagos_total, on="Cliente", how="left").fillna(0)
    saldos["Saldo pendiente"] = saldos["Total"] - saldos["Monto"]

    st.subheader("📋 Saldos pendientes por cliente")
    st.dataframe(
        saldos[["Cliente", "Total", "Monto", "Saldo pendiente"]].rename(columns={
            "Total": "Crédito otorgado",
            "Monto": "Pagos realizados"
        }),
        use_container_width=True
    )

    st.divider()
    st.subheader("🧾 Registrar nuevo pago")
    cliente_opciones = saldos["Cliente"].tolist()
    cliente = st.selectbox("Cliente", cliente_opciones)
    monto = st.number_input("Monto a abonar", min_value=0.0, format="%.2f")
    metodo_pago = st.selectbox("Método de pago", ["Efectivo", "Transferencia", "Tarjeta"])
    fecha = st.date_input("Fecha de pago")
    descripcion = st.text_input("Referencia del pago (opcional)")

    if st.button("Registrar pago"):
        pago_dict = {
            "Fecha": fecha.isoformat(),
            "Descripción": descripcion or f"Abono de crédito por parte de {cliente}",
            "Categoría": "Cobranza",
            "Tipo": "Ingreso",
            "Monto": float(monto),
            "Cliente": cliente,
            "Método de pago": metodo_pago
        }
        guardar_transaccion(pago_dict)
        st.success(f"✅ Pago de ${monto:.2f} registrado para {cliente}")

    st.divider()
    st.subheader("📑 Historial de pagos")
    if not pagos_cobranza.empty and all(col in pagos_cobranza.columns for col in ["Fecha", "Cliente", "Descripción", "Monto", "Método de pago"]):
        pagos_cobranza = pagos_cobranza[["Fecha", "Cliente", "Descripción", "Monto", "Método de pago"]]
        st.dataframe(pagos_cobranza.sort_values("Fecha", ascending=False), use_container_width=True)
    else:
        st.info("Aún no se han registrado pagos en la categoría 'Cobranza'.")
