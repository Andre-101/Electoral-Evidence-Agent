# User Interface

The dashboard is designed for end users.

## Main sections

- **Analizar**: run a demo or upload a CSV.
- **Reportes**: open generated reports.
- **Administración**: technical tools hidden behind admin mode.

The user does not need to understand internal IDs or pipeline steps.

## LLM rule

The UI does not allow selecting the LLM provider or model.

Provider and model are configured in `.env`. The UI can only request:

```text
use_llm=true
```

The backend decides whether Claude is available and which configured model should be used.
