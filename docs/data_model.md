# Data Model

## Main groups

| Group | Tables |
|---|---|
| Control | `ingestion_runs`, `source_files`, `source_mappings`, `rejected_records` |
| Catalogs | `countries`, `departments`, `municipalities`, `option_types`, `alert_catalog` |
| Electoral core | `elections`, `polling_stations`, `polling_tables`, `electoral_options`, `vote_results` |
| Metrics | `table_totals`, `table_metrics`, `option_table_metrics`, `station_metrics`, `municipality_metrics` |
| Alerts and scoring | `quality_alerts`, `eda_alerts`, `anomaly_scores`, `score_components`, `review_cases` |
| Evidence and reports | `evidence_items`, `evidence_dossiers`, `reports`, `report_exports`, `traceability_events` |
