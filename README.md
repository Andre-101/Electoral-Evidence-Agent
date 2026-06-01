# Electoral Evidence Agent

Electoral Evidence Agent is an application for processing tabular electoral results, detecting anomalous patterns, prioritizing review cases, generating structured evidence, and producing safe narrative reports for human review.

The system does **not** determine or confirm electoral fraud. It produces review evidence and prioritization signals based on deterministic analytics, with optional Claude integration for narrative drafting.

## What the application does

```text
CSV
→ ingestion
→ profiling
→ canonical mapping
→ electoral data model
→ quality validation
→ metrics
→ alerts
→ review scoring
→ review cases
→ evidence dossier
→ HTML reports
```

## Main features

- CSV ingestion and profiling.
- Canonical mapping of electoral columns.
- Electoral data model for departments, municipalities, polling stations, polling tables, candidates, parties and vote results.
- Quality validation.
- Electoral metrics and territorial comparison.
- Anomaly alerts.
- Review case prioritization.
- Structured evidence generation.
- Deterministic dossier generation.
- Optional Claude integration for dossier drafting.
- HTML case and executive reports.
- Streamlit dashboard.
- Automated demo pipeline.
- pytest test suite.

## Methodological principle

This project uses a `review_priority_score`, not a `fraud_score`.

The system identifies anomalies and possible irregularities that may justify human or documentary review. It does not accuse candidates, parties, polling officials or institutions, and it does not conclude fraud.

## Tech stack

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Polars
- Streamlit
- Jinja2
- Docker Compose
- pytest
- Optional: Anthropic Claude

## Requirements

- Docker Desktop
- Docker Compose
- Git
- PowerShell, Bash or a compatible terminal

No local Python installation is required for normal Docker-based usage.

## Quick start

Create the environment file:

```powershell
copy .env.example .env
```

Start the services:

```powershell
docker compose up --build
```

In another terminal, initialize the database:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api python db/seeds/seed_catalogs.py
docker compose exec api python db/seeds/seed_pilot_election.py
```

Run tests:

```powershell
docker compose exec api pytest
```

## Open the application

```text
Dashboard: http://localhost:8501
API docs:  http://localhost:8000/docs
Health:    http://localhost:8000/health
```

## Run the automated demo

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/demo/run"
```

Or open the dashboard and click:

```text
Analizar → Ejecutar demo
```

The demo generates:

- review cases,
- evidence dossier,
- case report,
- executive report.

Reports can be opened from the dashboard.

## Use your own CSV

Open the dashboard:

```text
http://localhost:8501
```

Then:

```text
Analizar → Cargar CSV → Analizar archivo
```

For best results, the CSV should include fields equivalent to:

```text
department
municipality
polling station
polling table
candidate or electoral option
party
votes
registered voters / census
```

The system can ingest different column names using aliases configured in `config/column_aliases.yaml`.

## Optional Claude integration

Claude is optional. The application works without an API key.

If `ANTHROPIC_API_KEY` is configured, Claude can draft the evidence dossier. If the key is missing, the API fails, or the output violates the language policy, the system falls back to deterministic dossier generation.

Add this to `.env`:

```env
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
LLM_ENABLED=auto
LLM_MAX_TOKENS=1800
```

The dashboard does not allow selecting provider or model. These values are operational configuration and must be defined in `.env`.

## Useful commands

Initialize database:

```powershell
./scripts/init.ps1
```

Run tests:

```powershell
./scripts/test.ps1
```

Run demo:

```powershell
./scripts/demo.ps1
```

Reset local environment:

```powershell
docker compose down -v
docker compose up --build
```

## Documentation

- [Setup](docs/setup.md)
- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [API](docs/api.md)
- [Data model](docs/data_model.md)
- [Demo](docs/demo.md)
- [Methodology and limits](docs/methodology.md)
- [Reports](docs/reports.md)
- [User interface](docs/ui.md)
- [Development](docs/development.md)

## Responsible use

The application is intended for:

- exploratory analysis,
- evidence organization,
- review prioritization,
- human analyst support.

It is not intended for:

- final legal determination,
- public accusation of individuals or organizations,
- automated decision-making without human review.

## Out of scope

- OCR or image processing.
- Official acta image validation.
- Authentication and role-based access control.
- Production deployment hardening.
- Real-time official electoral data integration.
- Legal or forensic determination of fraud.
