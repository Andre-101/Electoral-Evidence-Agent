# API

API docs are available at:

```text
http://localhost:8000/docs
```

## Health

```http
GET /health
GET /version
GET /llm/status
```

## Main pipeline

```http
POST /ingestions
POST /ingestions/{id}/profile
POST /ingestions/{id}/map
POST /ingestions/{id}/load-core
POST /ingestions/{id}/validate-quality
POST /ingestions/{id}/calculate-basic-metrics
POST /ingestions/{id}/calculate-territorial-metrics
POST /ingestions/{id}/generate-eda-alerts
POST /ingestions/{id}/calculate-scores
GET  /ingestions/{id}/review-cases
```

## Review cases

```http
GET  /review-cases/{id}
POST /review-cases/{id}/evidence-items/generate
GET  /review-cases/{id}/evidence-items
GET  /review-cases/{id}/agent-context
POST /review-cases/{id}/dossier
GET  /review-cases/{id}/dossier
```

## Reports

```http
POST /reports/case/{review_case_id}
POST /reports/executive/{ingestion_run_id}
GET  /reports/{report_id}
GET  /reports/{report_id}/html
```

## Demo

```http
POST /demo/run
```
