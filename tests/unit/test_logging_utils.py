from app.logging_utils import preview_for_log


def test_preview_collapses_newlines() -> None:
    s = preview_for_log("linea1\n\n\nlinea2   fin", max_len=200)
    assert "\n" not in s
    assert "linea1 linea2 fin" == s


def test_preview_strips_json_fence() -> None:
    s = preview_for_log('```json\n{"a": 1}\n```', max_len=200)
    assert "```" not in s
    assert '{"a": 1}' in s or "{a" in s.replace(" ", "")
