"""Impresion en consola de intercambios IA: bloques, JSON indentado (UTF-8).

Activar con IA_CONSOLE_PRETTY=true (por defecto True en Settings).
"""

from __future__ import annotations

import json
import sys
import textwrap
from typing import Any


def _strip_code_fence(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        lines = [ln for ln in t.splitlines() if not ln.strip().startswith("```")]
        t = "\n".join(lines).strip()
    return t


def _pretty_json_or_text(raw: str, *, max_lines: int = 200) -> str:
    """Intenta JSON con indent=2; si falla, devuelve texto tal cual (recortado por lineas)."""
    t = _strip_code_fence(raw)
    try:
        obj: Any = json.loads(t)
        out = json.dumps(obj, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        out = t
    lines = out.splitlines()
    if len(lines) > max_lines:
        tail = len(lines) - max_lines
        out = "\n".join(lines[:max_lines]) + f"\n... ({tail} lineas mas omitidas)"
    return out


def _is_mostly_json(body: str) -> bool:
    s = body.lstrip()
    if s.startswith("{") or s.startswith("["):
        return True
    if s.startswith("```"):
        return True
    if '"document_context"' in s[:800] and '"allowed_triples"' in s[:4000]:
        return True
    if '"allowed_subject_document_pairs"' in s[:4000]:
        return True
    return False


def _format_message_for_console(body: str, *, max_chars: int = 5000) -> str:
    if _is_mostly_json(body):
        return _pretty_json_or_text(body)
    chunk = body[:max_chars]
    if len(body) > max_chars:
        chunk += f"\n\n... [omitidos {len(body) - max_chars} caracteres; total {len(body)}]"
    try:
        return textwrap.fill(
            chunk,
            width=92,
            replace_whitespace=False,
            drop_whitespace=False,
        )
    except Exception:
        return chunk


def ia_pretty_enabled() -> bool:
    from app.config import get_settings

    return bool(get_settings().ia_console_pretty)


def print_ia_request_block(
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    messages: list[dict[str, str]],
) -> None:
    if not ia_pretty_enabled():
        return
    sep = "=" * 78
    # Simbolos simples compatibles con consolas Windows
    print(f"\n{sep}", file=sys.stdout, flush=True)
    print("  >> SOLICITUD IA", file=sys.stdout, flush=True)
    print(f"     modelo ........: {model}", file=sys.stdout, flush=True)
    print(f"     max_tokens ....: {max_tokens}", file=sys.stdout, flush=True)
    print(f"     temperature ...: {temperature}", file=sys.stdout, flush=True)
    print(sep, file=sys.stdout, flush=True)
    for i, msg in enumerate(messages):
        role = (msg.get("role") or "?").upper()
        content = msg.get("content") or ""
        print(
            f"\n  --- Mensaje [{i}]  ROL={role}  ({len(content)} caracteres) ---",
            file=sys.stdout,
            flush=True,
        )
        formatted = _format_message_for_console(content)
        for line in formatted.splitlines():
            print(f"    {line}", file=sys.stdout, flush=True)
    print(f"\n{sep}\n", file=sys.stdout, flush=True)


def print_ia_response_block(*, model: str, body: str) -> None:
    if not ia_pretty_enabled():
        return
    sep = "=" * 78
    print(f"\n{sep}", file=sys.stdout, flush=True)
    print("  << RESPUESTA IA", file=sys.stdout, flush=True)
    print(f"     modelo .......: {model}", file=sys.stdout, flush=True)
    print(f"     caracteres ...: {len(body)}", file=sys.stdout, flush=True)
    print(sep, file=sys.stdout, flush=True)
    print("", file=sys.stdout, flush=True)
    pretty = _pretty_json_or_text(body)
    for line in pretty.splitlines():
        print(f"    {line}", file=sys.stdout, flush=True)
    print(f"\n{sep}\n", file=sys.stdout, flush=True)
