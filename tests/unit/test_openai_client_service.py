from types import SimpleNamespace

from app.infrastructure.ai.openai_client_service import OpenAIClientService


class FakeCompletions:
    def create(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
        )


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        self.chat = FakeChat()


def test_openai_client_service_uses_legacy_client(monkeypatch) -> None:  # noqa: ANN001
    import app.infrastructure.ai.openai_client_service as module

    fake_openai_module = SimpleNamespace(OpenAI=FakeClient)
    monkeypatch.setattr(module.importlib, "import_module", lambda _: fake_openai_module)
    service = OpenAIClientService()
    response = service.create_chat_completion(
        messages=[{"role": "user", "content": "hola"}],
        model="gpt-4.1-mini",
        max_tokens=50,
        temperature=0.1,
    )
    assert response == '{"ok": true}'
