# Contributing

## Development rules

- Keep LLM usage optional.
- Do not introduce features that claim or confirm fraud.
- Add tests for new services and endpoints.
- Keep configuration in YAML when possible.
- Preserve traceability for generated evidence, dossiers and reports.

## Before opening a PR

Run:

```powershell
docker compose exec api pytest
```

Expected result:

```text
29 passed
```
