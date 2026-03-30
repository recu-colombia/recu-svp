# Integracion recu-judicial -> recu-SVP-nuevo

## Objetivo

Migrar de contrato legado (`/analyze`) a contrato v2 (`/v2/analyze-auto`) con rollout controlado y sin interrupcion del poblamiento.

## Contrato v2

### Request

```json
{
  "proceso_id": 123,
  "actuacion_fuente_id": 456,
  "url_auto": "https://storage/.../auto.pdf",
  "modo": "preview",
  "frases_contexto": []
}
```

### Response

```json
{
  "estado": "ok",
  "actuaciones_generadas": [
    {
      "actuacion_fuente_id": 456,
      "id_sujeto": 2,
      "id_tipo_documento": 4,
      "id_verbo": 12,
      "id_complemento_directo": 33,
      "id_regla": 80,
      "antecedente_id": 444,
      "complemento_indirecto_text": "CONTRA EL AUTO...",
      "texto_final": "SUJETO(2) DOC(4)...",
      "estado": "clasificada_con_regla",
      "confianza_ia": 0.83,
      "trace": {
        "model_path": "cheap",
        "rule_id": 80
      }
    }
  ],
  "sin_clasificar": [],
  "errores": []
}
```

## Estrategia de migracion

1. **Fase 1 - Doble escritura logica (preview):** judicial llama v2 y no persiste automaticamente; solo compara resultados con flujo actual.
2. **Fase 2 - Canary por porcentaje:** activar persistencia (`modo=commit`) para un subconjunto de procesos.
3. **Fase 3 - Rollout completo:** mover todo poblamiento a v2 y mantener `/analyze` solo como fallback temporal.
4. **Fase 4 - Retiro legado:** eliminar integracion con contrato anterior.

## Cambios requeridos en recu-judicial

- Actualizar cliente de microservicio para enviar `url_auto` y `actuacion_fuente_id`.
- Mapear `actuaciones_generadas[]` a insercion/actualizacion de actuaciones.
- Guardar trazabilidad (`trace`) para auditoria funcional.
- Aplicar retries idempotentes por `actuacion_fuente_id`.

## Conexion a base de datos (decision)

Para este caso se adopta **conexion directa del microservicio recu-SVP-nuevo a PostgreSQL judicial**
en modo **read-only** para consultar:

- reglas del schema `svp`,
- catalogos (`tipos_*`, conectores, patrones),
- actuaciones previas para seleccionar antecedente.

Justificacion:

1. Menor latencia en consultas de reglas/antecedentes (menos saltos de red).
2. Menor complejidad operativa que encadenar judicial->judicial-interno->SVP.
3. Mejor escalabilidad para alto volumen de solicitudes de clasificacion.

Regla operativa:

- `recu-SVP-nuevo` **lee** de PostgreSQL.
- `recu-judicial` mantiene la responsabilidad de persistencia funcional final y
  orquestacion del flujo de negocio.
