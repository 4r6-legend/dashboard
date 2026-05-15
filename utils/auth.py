"""Autenticação com bcrypt — usuários apenas via Streamlit Secrets (sem senhas no repositório)."""

from __future__ import annotations

import bcrypt
import streamlit as st
from typing import Dict


def get_users() -> Dict[str, str]:
    """Retorna e-mail -> hash bcrypt configurado em [credentials.users] no secrets."""
    try:
        users = st.secrets["credentials"]["users"]
        return dict(users) if users else {}
    except Exception:
        return {}


def authenticate(username: str, password: str) -> bool:
    users = get_users()
    if not users or not username or not password:
        return False
    if username not in users:
        return False
    hashed = users[username]
    if isinstance(hashed, str):
        hashed = hashed.encode()
    return bcrypt.checkpw(password.encode(), hashed)
