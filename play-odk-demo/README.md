# Play ODK farmer sample pipeline

Artifacts for the play-namespace ODK → Connector → Farmer Registry Partner path.

## Pieces

| Piece | Where |
|-------|--------|
| ODK form | `farmer_registration.xml` (published on ODK project **Play Farmer Demo**) |
| Jinja mapping | `odk_to_openg2p_farmer.json.j2` → MinIO bucket `templates` |
| Partner rules | `seed_odk_farmer_rules.sql` (data model `ODK_FARMER_V1`, sender `odk-farmer-play`) |
| Connector | `ODK Play Farmer Registration` on https://connector.play.openg2p.org |

## Flow

1. Submit `farmer_registration` on https://odk.play.openg2p.org (project Play Farmer Demo).
2. Connector polls ODK Central (`odk_central` + `odk_session`).
3. Partner ingest uses `data_model=ODK_FARMER_V1`, sender `odk-farmer-play`, register `Farmer`.
4. Celery classify → transform (Jinja) → ingest into intake form sections (`fr_farmer_*`).

## Connector shape

- `g2p_sender_id`: `odk-farmer-play`
- `g2p_register_mnemonic`: `Farmer`
- `data_model_mnemonic`: `ODK_FARMER_V1`
- `source_config_json`: `base_url=https://odk.play.openg2p.org`, `project_id=1`, `form_id=farmer_registration`

## Re-seed / re-upload

```bash
# Partner mapping rules
kubectl -n play cp play-odk-demo/seed_odk_farmer_rules.sql commons-postgresql-0:/tmp/
kubectl -n play exec commons-postgresql-0 -- sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -U postgres -d farmer_registry -f /tmp/seed_odk_farmer_rules.sql'

# Jinja to MinIO (from commons-minio pod)
kubectl -n play cp play-odk-demo/odk_to_openg2p_farmer.json.j2 <minio-pod>:/tmp/
# then: mc cp /tmp/odk_to_openg2p_farmer.json.j2 local/templates/
```

## Notes

- Partner lookup needs `master_data.g2p_partners` row for mnemonic `odk-farmer-play`.
- Partner API needs `REGISTRY_PARTNER_API_MASTER_DATA_DB_*` pointed at `commons-postgresql` / `master_data`.
- Jinja section keys must be `fr_farmer_personal_info`, `fr_farmer_socio_and_health`, `fr_farmer_location`.
- `source_of_income` values must use `SOI_*` enums; leave lat/long as JSON `null`.
