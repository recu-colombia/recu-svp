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
  "frases_contexto": [],
  "fecha_ocurrencia_referencia": "2026-03-17"
}
```

- `fecha_ocurrencia_referencia` (opcional, `date`): si judicial la envia, el microservicio filtra candidatos a antecedente con `fecha_ocurrencia` nula o menor o igual a esa fecha. Si se omite, no se aplica filtro temporal.
- `actuacion_fuente_id`: id de `public.actuacion` que se esta analizando; se excluye de la busqueda de antecedentes.

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
        "model_path": "p3_skipped_single_candidate",
        "rule_id": 80,
        "candidatos_antecedente": 1,
        "p3_invocado": false,
        "antecedente_search_skipped": false,
        "filtro_fecha_aplicado": true,
        "candidatos_truncados": false
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

- Actualizar cliente de microservicio para enviar `url_auto`, `actuacion_fuente_id` y, cuando exista, `fecha_ocurrencia_referencia` (fecha de ocurrencia de la actuacion analizada).
- Mapear `actuaciones_generadas[]` a insercion/actualizacion de `public.actuacion` al persistir (commit): al menos `id_sujeto`, textos/IDs de tipo documento, verbo, complemento directo, `id_regla`, `id_antecedente`, `complemento_indirecto`, `frase_concatenada` desde `texto_final`, `analisis_svp` si aplica.
- Guardar trazabilidad (`trace`) para auditoria funcional.
- Aplicar retries idempotentes por `actuacion_fuente_id`.

### Mapper sugerido (DTO -> `Actuacion`)

| Campo respuesta v2 | Columna judicial (referencia) |
|--------------------|-------------------------------|
| `texto_final` | `frase_concatenada` |
| `id_regla` | `id_regla` |
| `antecedente_id` | `id_antecedente` |
| `complemento_indirecto_text` | `complemento_indirecto` |
| `id_sujeto`, `id_tipo_documento`, `id_verbo`, `id_complemento_directo` | homonimos + columnas de texto enriquecido si aplica |

## Conexion a base de datos (decision)

Para este caso se adopta **conexion directa del microservicio recu-SVP-nuevo a PostgreSQL judicial**
en modo **read-only** para consultar:

- reglas del schema `svp`,
- catalogos (`tipos_*`, conectores, patrones),
- actuaciones previas en `public.actuacion` (mismo `id_proceso` que `proceso_id` del request) para seleccionar antecedente segun criterios de `svp.reglas_gramaticales_encadenamiento` y patron `svp.patrones_concatenacion.codigo`.

Variables de entorno relacionadas (ver `.env` / `config.py`): `judicial_actuacion_table` (por defecto `public.actuacion`), `max_antecedent_candidates` (por defecto 10, tope de candidatos devueltos antes de P3).

Justificacion:

1. Menor latencia en consultas de reglas/antecedentes (menos saltos de red).
2. Menor complejidad operativa que encadenar judicial->judicial-interno->SVP.
3. Mejor escalabilidad para alto volumen de solicitudes de clasificacion.

Regla operativa:

- `recu-SVP-nuevo` **lee** de PostgreSQL.
- `recu-judicial` mantiene la responsabilidad de persistencia funcional final y
  orquestacion del flujo de negocio.
