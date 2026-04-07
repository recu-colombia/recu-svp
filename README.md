# recu-SVP-nuevo

Microservicio SVP v2 para analizar autos, resolver reglas de concatenacion sobre `svp` y devolver actuaciones candidatas para poblamiento en `recu-judicial`.

## Stack

- Python 3.13
- FastAPI
- SQLAlchemy + PostgreSQL
- Pydantic Settings con `.env`
- Capa IA enrutable (`cheap -> strong`) por puerto `LanguageModel`

## Ejecutar local

1. Crear entorno virtual con Python 3.13.
2. Instalar dependencias:
   - `python -m pip install -e .[dev]`
3. Copiar `.env.example` a `.env` y ajustar valores.
4. Ejecutar:
   - `uvicorn app.main:app --reload --port 8002`

## Variables OpenAI (estilo legacy)

- `OPENAI_API_KEY`: llave API.
- `OPENAI_BASE_URL`: URL base opcional (proxy o endpoint compatible).
- `AI_MODEL_CHEAP`: modelo de primera pasada.
- `AI_MODEL_STRONG`: modelo de fallback.
- `AI_MAX_TOKENS`: limite por llamada.
- `AI_TEMPERATURE`: temperatura de generación.
- `AI_TIMEOUT`: timeout de cliente.
- `AI_MAX_RETRIES`: reintentos máximos del flujo.

Ejemplo rapido:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
AI_MODEL_CHEAP=gpt-4.1-mini
AI_MODEL_STRONG=gpt-4.1
AI_MAX_TOKENS=1000
AI_TEMPERATURE=0.1
```

## Endpoint principal

- `POST /v2/analyze-auto`

## Calidad

- `ruff check .`
- `black --check .`
- `mypy app`
- `pytest`
