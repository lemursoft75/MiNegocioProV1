# utils/db.py
import os
import json
import base64
import logging
import pandas as pd
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

db = None  # cliente global Firestore


# ---------------------------
# Inicializar Firebase una sola vez
# ---------------------------
def inicializar_firebase():
    global db
    if db is not None:
        return
    if not firebase_admin._apps:
        # 1) Prioridad: secreta B64
        if "FIREBASE_PRIVATE_KEY_B64" in st.secrets:
            b64_str = st.secrets["FIREBASE_PRIVATE_KEY_B64"].replace("\n", "").replace("\r", "").strip()
            cred_dict = json.loads(base64.b64decode(b64_str).decode("utf-8"))
            cred = credentials.Certificate(cred_dict)
        # 2) Diccionario directo en secrets
        elif isinstance(st.secrets.get("SERVICE_ACCOUNT", None), dict):
            cred = credentials.Certificate(st.secrets["SERVICE_ACCOUNT"])
        # 3) JSON string en secrets
        else:
            cred_dict = json.loads(st.secrets["SERVICE_ACCOUNT"])
            cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    db = firestore.client()


# ---------------------------
# Helpers
# ---------------------------
def _uid():
    return st.session_state.get("uid")


def _ref_user(col):
    uid = _uid()
    if not uid:
        return None
    return db.collection("usuarios").document(uid).collection(col)


def _ref_write(col):
    """Siempre escribe bajo el usuario actual."""
    inicializar_firebase()
    ref = _ref_user(col)
    if ref is None:
        raise RuntimeError("⚠️ No hay UID en sesión, no se puede escribir.")
    return ref


# ---------- Lectura base cacheada (solo user) ----------
def _cached_read_union(col: str, columnas: list, uid: str | None):
    """
    Lee solo datos del usuario actual (usuarios/{uid}/{col}).
    """
    inicializar_firebase()

    if not uid:
        return pd.DataFrame(columns=columnas)

    ref_user = db.collection("usuarios").document(uid).collection(col)
    docs_user = list(ref_user.stream())

    if not docs_user:
        return pd.DataFrame(columns=columnas)

    df_user = pd.DataFrame([{c: d.to_dict().get(c, None) for c in columnas} for d in docs_user])

    # Asegurar columnas
    for c in columnas:
        if c not in df_user.columns:
            df_user[c] = None

    # Deduplicar por Clave si aplica
    if "Clave" in columnas and "Clave" in df_user.columns:
        df_user = df_user.drop_duplicates(subset=["Clave"], keep="first")

    return df_user[columnas]


def _clear_cache():
    # Limpiar cache de lecturas tras cualquier escritura
    st.cache_data.clear()


# ---------------------------
# Ventas
# ---------------------------
def guardar_venta(venta_dict):
    _ref_write("ventas").add(venta_dict)
    logging.info("Venta guardada.")
    _clear_cache()


def leer_ventas():
    columnas = [
        "Fecha", "Cliente", "Producto", "Clave del Producto",
        "Cantidad", "Precio Unitario", "Total", "Descuento", "Importe Neto",
        "Monto Crédito", "Monto Contado", "Anticipo Aplicado",
        "Método de pago", "Tipo de venta"
    ]
    uid = _uid()
    df = _cached_read_union("ventas", columnas, uid)
    for col in ["Cantidad", "Precio Unitario", "Total", "Descuento", "Importe Neto",
                "Monto Crédito", "Monto Contado", "Anticipo Aplicado"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


# ---------------------------
# Clientes
# ---------------------------
def guardar_cliente(id_cliente, cliente_dict):
    _ref_write("clientes").document(id_cliente).set(cliente_dict)
    logging.info(f"Cliente '{id_cliente}' guardado.")
    _clear_cache()


def actualizar_cliente(id_cliente, datos_nuevos):
    _ref_write("clientes").document(id_cliente).update(datos_nuevos)
    logging.info(f"Cliente '{id_cliente}' actualizado.")
    _clear_cache()


def leer_clientes():
    columnas = ["ID", "Nombre", "Correo", "Teléfono", "Empresa", "RFC", "Límite de crédito"]
    inicializar_firebase()
    uid = _uid()
    if not uid:
        return pd.DataFrame(columns=columnas)

    ref = db.collection("usuarios").document(uid).collection("clientes")
    docs = list(ref.stream())
    if not docs:
        return pd.DataFrame(columns=columnas)

    filas = []
    for d in docs:
        data = d.to_dict() or {}
        data["ID"] = d.id
        filas.append({c: data.get(c, None) for c in columnas})
    df = pd.DataFrame(filas)

    if "Límite de crédito" in df.columns:
        df["Límite de crédito"] = pd.to_numeric(df["Límite de crédito"], errors="coerce").fillna(0.0)
    return df[columnas]


# ---------------------------
# Transacciones
# ---------------------------
def guardar_transaccion(transaccion_dict):
    _ref_write("transacciones").add(transaccion_dict)
    logging.info("Transacción guardada.")
    _clear_cache()


def registrar_pago_cobranza(cliente, monto, metodo_pago, fecha, descripcion=""):
    pago_dict = {
        "Fecha": fecha,
        "Descripción": descripcion or f"Abono de crédito por parte de {cliente}",
        "Categoría": "Cobranza",
        "Tipo": "Ingreso",
        "Monto": monto,
        "Cliente": cliente,
        "Método de pago": metodo_pago,
    }
    _ref_write("transacciones").add(pago_dict)
    logging.info("Pago de cobranza registrado.")
    _clear_cache()


def leer_transacciones():
    columnas = ["Fecha", "Descripción", "Categoría", "Tipo", "Monto", "Cliente", "Método de pago"]
    uid = _uid()
    df = _cached_read_union("transacciones", columnas, uid)
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
    return df


def leer_cobranza():
    df = leer_transacciones()
    return df[df["Categoría"] == "Cobranza"]


def calcular_balance_contable():
    df = leer_transacciones()
    ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
    egresos = df[df["Tipo"] == "Egreso"]["Monto"].sum()
    return ingresos, egresos, ingresos - egresos


# ---------------------------
# Productos
# ---------------------------
def guardar_producto(producto_dict):
    for campo in ["Marca_Tipo", "Modelo", "Color", "Talla"]:
        producto_dict.setdefault(campo, "")
    _ref_write("productos").add(producto_dict)
    logging.info("Producto guardado.")
    _clear_cache()


def actualizar_producto_por_clave(clave, campos_actualizados):
    for campo in ["Marca_Tipo", "Modelo", "Color", "Talla"]:
        campos_actualizados.setdefault(campo, "")

    inicializar_firebase()
    ref_user = _ref_user("productos")
    if ref_user is None:
        return

    q_user = ref_user.where("Clave", "==", clave).get()
    if q_user:
        ref_user.document(q_user[0].id).update(campos_actualizados)
        logging.info(f"Producto '{clave}' actualizado.")
        _clear_cache()


def eliminar_producto_por_clave(clave):
    ref = _ref_write("productos")
    q = ref.where("Clave", "==", clave).get()
    if q:
        ref.document(q[0].id).delete()
        logging.info(f"Producto '{clave}' eliminado.")
        _clear_cache()


def obtener_id_producto(clave):
    df = leer_productos()
    fila = df[df["Clave"] == clave]
    return fila.index[0] if not fila.empty else None


def leer_productos():
    columnas = [
        "Clave", "Nombre", "Marca_Tipo", "Modelo", "Color", "Talla",
        "Categoría", "Precio Unitario", "Costo Unitario", "Cantidad", "Descripción"
    ]
    uid = _uid()
    df = _cached_read_union("productos", columnas, uid)
    for col in ["Precio Unitario", "Costo Unitario", "Cantidad"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df