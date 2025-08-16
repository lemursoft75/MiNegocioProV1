import streamlit as st
import firebase_admin
from firebase_admin import auth
import pyrebase  # pip install pyrebase4
import datetime

# 🔹 Configuración de Firebase para cliente (Pyrebase)

firebaseConfig = dict(st.secrets["firebase_client"])
firebase = pyrebase.initialize_app(firebaseConfig)
auth_client = firebase.auth()


# ---------------------------
# Registro de usuario
# ---------------------------
def registrar_usuario(correo, contrasena):
    try:
        user = auth.create_user(
            email=correo,
            password=contrasena
        )
        st.success("✅ Usuario registrado correctamente")
    except Exception as e:
        st.error(f"❌ Error al registrar usuario: {e}")


# ---------------------------
# Inicio de sesión
# ---------------------------
def iniciar_sesion(correo, contrasena):
    try:
        user = auth_client.sign_in_with_email_and_password(correo, contrasena)
        st.session_state.uid = user["localId"]      # 👈 UID para particionar datos
        st.session_state.usuario = correo
        st.success("✅ Inicio de sesión exitoso")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error al iniciar sesión: {e}")



# ---------------------------
# Cerrar sesión
# ---------------------------
def cerrar_sesion():
    for k in ["uid", "usuario"]:
        if k in st.session_state:
            del st.session_state[k]
    st.success("👋 Sesión cerrada exitosamente")



# ---------------------------
# Recuperar contraseña
# ---------------------------
def recuperar_contrasena(correo):
    try:
        auth_client.send_password_reset_email(correo)
        st.success(f"✅ Se envió un correo de recuperación a: {correo}")
    except Exception as e:
        st.error(f"❌ Error al enviar recuperación: {e}")


# ---------------------------
# Pantalla de login
# ---------------------------
def mostrar_login():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h1 style='color: #2C3E50;'>💼 MiNegocio Pro</h1>
            <h4 style='color: #7F8C8D;'>- By Xibalbá Business -</h4>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔐 Iniciar sesión o Registrarse")
    opcion = st.radio("Selecciona una opción", ["Iniciar sesión", "Registrar nuevo", "Recuperar contraseña"])

    if opcion == "Iniciar sesión":
        correo = st.text_input("Correo")
        contrasena = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            iniciar_sesion(correo, contrasena)

    elif opcion == "Registrar nuevo":
        correo = st.text_input("Correo")
        contrasena = st.text_input("Contraseña", type="password")
        if st.button("Registrar"):
            registrar_usuario(correo, contrasena)

    elif opcion == "Recuperar contraseña":
        correo = st.text_input("Correo para recuperación")
        if st.button("Enviar recuperación"):
            recuperar_contrasena(correo)


# ---------------------------
# Mostrar botón de logout
# ---------------------------
def mostrar_logout():
    if "usuario" in st.session_state:
        st.sidebar.markdown(f"👤 Usuario: {st.session_state.usuario}")
        if st.sidebar.button("Cerrar sesión"):
            cerrar_sesion()