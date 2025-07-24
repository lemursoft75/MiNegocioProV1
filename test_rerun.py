import streamlit as st

st.write("¡Prueba de experimental_rerun!")

if st.button("Recargar"):
    st.experimental_rerun()
