"""Nome da organização apenas via Streamlit Secrets (`[gobrax].display_name`). Sem valor default de marca."""

from __future__ import annotations

import re

__all__ = ["get_display_name", "get_file_slug", "require_display_name"]


def get_display_name() -> str:
    """Retorna o nome configurado ou string vazia se ausente."""
    import streamlit as st

    try:
        raw = st.secrets["gobrax"]["display_name"]
        return str(raw).strip()
    except Exception:
        return ""


def require_display_name() -> str:
    """Garante que `[gobrax].display_name` existe e não é vazio; caso contrário interrompe a app."""
    import streamlit as st

    name = get_display_name()
    if not name:
        st.error(
            "Defina nos Secrets a chave `[gobrax].display_name` (texto da organização exibido no app)."
        )
        st.stop()
    return name


def get_file_slug() -> str:
    """Slug para nomes de CSV; genérico se não houver nome configurado."""
    name = get_display_name()
    if not name:
        return "billing"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return slug or "billing"
