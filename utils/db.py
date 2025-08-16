# utils/db.py
import os
import json
import base64
import datetime
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


def _ref_root(col):
    return db.collection(col)


def _ref_write(col):
    """Para ESCRIBIR: usa espacio usuario si hay uid; si no, raíz (para pruebas)."""
    inicializar_firebase()
    ref = _ref_user(col)
    return ref if ref is not None else _ref_root(col)


# ---------- Lectura base cacheada (UNE user + root) ----------
# @st.cache_data(ttl=60, max_entries=100)
def _cached_read_union(col: str, columnas: list, uid: str | None):
    """
    Une datos de usuarios/{uid}/{col} + {col} en raíz.
    Si hay duplicados (p.ej. misma 'Clave'), se respeta primero lo del usuario.
    """
    inicializar_firebase()

    # 1) Usuario
    df_user = pd.DataFrame(columns=columnas)
    if uid:
        ref_user = db.collection("usuarios").document(uid).collection(col)
        docs_user = list(ref_user.stream())
        if docs_user:
            df_user = pd.DataFrame([{c: d.to_dict().get(c, None) for c in columnas} for d in docs_user])

    # 2) Raíz
    ref_root = _ref_root(col)
    docs_root = list(ref_root.stream())
    df_root = pd.DataFrame([{c: d.to_dict().get(c, None) for c in columnas} for d in docs_root]) if docs_root else pd.DataFrame(columns=columnas)

    # 3) Unir: primero user (para que conserve prioridad), luego root
    df = pd.concat([df_user, df_root], ignore_index=True)

    # Asegurar columnas
    for c in columnas:
        if c not in df.columns:
            df[c] = None

    # Si existe 'Clave', deduplicar por Clave conservando la 1ª ocurrencia (usuario)
    if "Clave" in columnas and "Clave" in df.columns:
        df = df.drop_duplicates(subset=["Clave"], keep="first")

    return df[columnas]



def _clear_cache():
    # Limpiar cache de lecturas tras cualquier escritura
    st.cache_data.clear()


# ---------------------------
# Ventas
# ---------------------------
def guardar_venta(venta_dict):
    ref = _ref_write("ventas")
    ref.add(venta_dict)
    logging.info("Venta guardada.")
    _clear_cache()


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

    # 1) Intentar en la colección del usuario
    ref_user = _ref_user("productos")
    if ref_user is not None:
        q_user = ref_user.where("Clave", "==", clave).get()
        if q_user:
            ref_user.document(q_user[0].id).update(campos_actualizados)
            logging.info(f"Producto '{clave}' actualizado (usuario).")
            _clear_cache()
            return

    # 2) Intentar en la colección raíz
    ref_root = _ref_root("productos")
    q_root = ref_root.where("Clave", "==", clave).get()
    if q_root:
        ref_root.document(q_root[0].id).update(campos_actualizados)
        logging.info(f"Producto '{clave}' actualizado (raíz).")
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


# ---------------------------
# Lecturas públicas (envuelven la cache con uid actual)
# ---------------------------
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


def leer_ventas():
    columnas = [
        "Fecha", "Cliente", "Producto", "Clave del Producto",  # <-- ¡Aquí está el cambio!
        "Cantidad", "Precio Unitario", "Total", "Descuento", "Importe Neto",
        "Monto Crédito", "Monto Contado", "Anticipo Aplicado", "Método de pago", "Tipo de venta"
    ]
    uid = _uid()
    df = _cached_read_union("ventas", columnas, uid)
    for col in ["Cantidad", "Precio Unitario", "Total", "Descuento", "Importe Neto",
                "Monto Crédito", "Monto Contado", "Anticipo Aplicado"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


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


def leer_clientes():
    columnas = ["ID", "Nombre", "Correo", "Teléfono", "Empresa", "RFC", "Límite de crédito"]
    inicializar_firebase()
    uid = _uid()

    def _docs_to_df(ref):
        docs = list(ref.stream())
        if not docs:
            return pd.DataFrame(columns=columnas)
        filas = []
        for d in docs:
            data = d.to_dict() or {}
            data["ID"] = d.id
            filas.append({c: data.get(c, None) for c in columnas})
        return pd.DataFrame(filas)

    df_user = _docs_to_df(db.collection("usuarios").document(uid).collection("clientes")) if uid else pd.DataFrame(columns=columnas)
    df_root = _docs_to_df(_ref_root("clientes"))

    # Usuario primero -> prioridad
    df = pd.concat([df_user, df_root], ignore_index=True)

    # Asegurar columnas
    for c in columnas:
        if c not in df.columns:
            df[c] = None

    # Dedup por ID si existe
    if "ID" in df.columns:
        df = df.drop_duplicates(subset=["ID"], keep="first")

    if "Límite de crédito" in df.columns:
        df["Límite de crédito"] = pd.to_numeric(df["Límite de crédito"], errors="coerce").fillna(0.0)
    return df[columnas]
