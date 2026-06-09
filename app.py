import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="Saperka vs Kurierzy",
    page_icon="🪖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container {
        padding-top: 0.75rem;
        padding-bottom: 0;
        max-width: 1200px;
      }
      header, footer {
        visibility: hidden;
      }
      iframe {
        border-radius: 16px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

html = Path("index.html").read_text(encoding="utf-8")

# Gra jest zwykłym HTML/CSS/JS, więc w Streamlit najlepiej działa jako komponent iframe.
components.html(html, height=760, scrolling=False)
