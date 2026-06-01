# Development

## Run tests

```powershell
docker compose exec api pytest
```

## Add a rule

1. Add the rule to `config/rules.yaml`.
2. Register the alert code in seeds if needed.
3. Implement evaluation in the relevant service.
4. Add tests.

## Add a metric

1. Update the model if needed.
2. Update migrations/schema.
3. Implement calculation in `MetricsService`.
4. Add tests.

## Add report content

1. Update templates in `app/reports/templates`.
2. Update `ReportService`.
3. Add tests.

## LLM development rule

LLM usage must remain optional and must always have deterministic fallback.
