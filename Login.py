"""
Billing dashboard — tela de login (layout alinhado ao cog.tools.engenharia-assistant).
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from utils.auth import authenticate
from utils import get_display_name

_ROOT = Path(__file__).resolve().parent
_ORG = get_display_name()

st.set_page_config(
    page_title=f"Login — {_ORG} Billing",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}

        .stButton > button {
            background-color: #0049FF;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            width: 100%;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #0038CC;
            box-shadow: 0 4px 12px rgba(0, 73, 255, 0.3);
        }
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            padding: 12px;
            font-size: 15px;
        }
        .stTextInput > div > div > input:focus {
            border-color: #0049FF;
            box-shadow: 0 0 0 2px rgba(0, 73, 255, 0.1);
        }
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    st.switch_page("pages/01_💰_Billing_Dashboard.py")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(
        "<h2 style='text-align: center; color: #0049FF; font-weight: 600; font-size: 2.1rem; margin-bottom: 8px; margin-top: 12px;'>Tela de autenticação</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #666; font-size: 15px; margin-bottom: 30px;'>"
        "Entre com suas credenciais para continuar.</p>",
        unsafe_allow_html=True,
    )

    username = st.text_input(
        "Usuário",
        placeholder="seu-email@cognitivo.ai",
        label_visibility="visible",
    )
    password = st.text_input(
        "Senha",
        type="password",
        placeholder="Digite sua senha",
        label_visibility="visible",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    login_button = st.button("Login", type="primary", use_container_width=True)

    if login_button:
        if username and password:
            if authenticate(username, password):
                st.success("Login realizado com sucesso.")
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                time.sleep(0.6)
                st.switch_page("pages/01_💰_Billing_Dashboard.py")
            else:
                st.error("Usuário ou senha incorretos.")
        else:
            st.warning("Preencha usuário e senha.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_b:
        logo_path = _ROOT / "assets" / "images" / "logo_cog.png"
        if logo_path.is_file():
            st.image(str(logo_path), width=120)
