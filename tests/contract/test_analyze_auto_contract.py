from fastapi.testclient import TestClient

from app.main import app
from app.interfaces.http.v2.schemas import AnalyzeAutoV2Response, ActuacionGeneradaDTO


class FakeUseCase:
    async def execute(self, request):  # noqa: ANN001
        _ = request
        return AnalyzeAutoV2Response(
            estado="ok",
            actuaciones_generadas=[
                ActuacionGeneradaDTO(
                    actuacion_fuente_id=999,
                    id_sujeto=2,
                    id_tipo_documento=4,
                    id_verbo=12,
                    id_complemento_directo=33,
                    id_regla=80,
                    antecedente_id=10,
                    complemento_indirecto_text="CONTRA AUTO",
                    texto_final="TEST",
                    estado="clasificada_con_regla",
                    confianza_ia=0.91,
                    trace={"model_path": "cheap->strong"},
                )
            ],
        )


def test_analyze_auto_v2_contract(monkeypatch) -> None:  # noqa: ANN001
    import app.interfaces.http.v2.routes as routes_module

    monkeypatch.setattr(routes_module, "build_analyze_auto_use_case", lambda: FakeUseCase())
    client = TestClient(app)
    payload = {
        "proceso_id": 1,
        "actuacion_fuente_id": 999,
        "url_auto": "https://example.com/auto.pdf",
        "modo": "preview",
        "frases_contexto": [],
    }
    response = client.post("/v2/analyze-auto", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["actuaciones_generadas"][0]["trace"]["model_path"] == "cheap->strong"
