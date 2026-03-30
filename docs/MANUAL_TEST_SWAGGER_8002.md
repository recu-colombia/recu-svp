# Pruebas manuales en Swagger (puerto 8002)

## 1) Levantar servicio

Desde `recu-SVP-nuevo`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Abrir:

- `http://127.0.0.1:8002/docs`

## 2) Endpoint de salud

- `GET /health`
- Esperado: `{"status":"ok"}`

## 3) Probar procesamiento real

Endpoint:

- `POST /v2/analyze-auto`

Payload ejemplo:

```json
{
  "proceso_id": 12345,
  "actuacion_fuente_id": 99999,
  "url_auto": "https://<url-publica-o-interna>/auto.pdf",
  "modo": "preview",
  "frases_contexto": []
}
```

## 4) Como interpretar respuesta

### Caso correcto
- `estado = "ok"`
- `actuaciones_generadas` con IDs reales y `trace`.

### Caso parcial
- `estado = "partial"`
- revisar `sin_clasificar` y `errores`.
- ejemplos: identificacion IA invalida o sin reglas aplicables.

### Caso error
- `estado = "error"`
- error de descarga/parseo PDF.

## 5) Importante sobre el ejemplo de Swagger

Los valores `0`, `string`, `additionalProp1` son **solo ejemplo de schema OpenAPI**.
No representan resultado real del procesamiento.

Debes ejecutar **Try it out** con tu payload y revisar la respuesta del bloque **Response body**.
