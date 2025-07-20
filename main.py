import streamlit as st
from streamlit_option_menu import option_menu

# 👉 Importar módulos
from modules.clientes import render as render_clientes
from modules.ventas import render as render_ventas
from modules.dashboard import render as render_dashboard
from modules.contabilidad import render as render_contabilidad
from modules.productos import render as render_productos
from modules.cobranza import render as render_cobranza


st.set_page_config(page_title="Defontana PYME", layout="wide")

with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with st.sidebar:
    selected = option_menu(
        "Menú Principal",
        ["📊 Dashboard", "💸 Ventas", "🧾 Contabilidad", "👥 Clientes", "📦 Productos", "💳 Cobranza"],
        icons=["bar-chart", "cash-coin", "clipboard-data", "people", "box", "credit-card"],
        menu_icon="briefcase", default_index=0
    )

# 🧭 Navegación modular
if selected == "📊 Dashboard":
    render_dashboard()
elif selected == "💸 Ventas":
    render_ventas()
elif selected == "🧾 Contabilidad":
    render_contabilidad()
elif selected == "👥 Clientes":
    render_clientes()
elif selected == "💳 Cobranza":
    render_cobranza()
elif selected == "📦 Productos":
    render_productos()