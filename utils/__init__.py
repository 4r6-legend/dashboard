"""Helpers partilhados (nome da org via Secrets)."""

from __future__ import annotations

import re

import streamlit as st

_DEFAULT_ORG = "Gobrax"


def get_display_name() -> str:
    try:
        s = str(st.secrets["gobrax"]["display_name"]).strip()
        return s or _DEFAULT_ORG
    except Exception:
        return _DEFAULT_ORG


def get_file_slug() -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", get_display_name()).strip("_").lower()
    return slug or "org"


__all__ = ["get_display_name", "get_file_slug"]
