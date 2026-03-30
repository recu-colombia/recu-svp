"""Utilidades para mensajes de log legibles (una linea, sin saltos que rompan la consola)."""

from __future__ import annotations

import re


def preview_for_log(text: str | None, *, max_len: int = 2000) -> str:
    if text is None:
        return "<none>"
    s = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not s:
        return "<empty>"

    if s.startswith("```"):
        lines = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
        s = "\n".join(lines).strip()

    s = re.sub(r"\s+", " ", s)
    if len(s) <= max_len:
        return s
    head = max_len - 24
    return f"{s[:head]}... [total {len(s)} chars]"
