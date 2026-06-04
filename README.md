# Electoral Evidence Agent

Electoral Evidence Agent is a functional application for analyzing structured electoral results, identifying atypical signals, and generating clear reports with visualizations.

The system does not determine or confirm electoral fraud. It highlights patterns in the loaded data and explains them in neutral language.

## What it does

```text
CSV data
-> ingestion
-> mapping
-> metrics
-> atypical signal detection
-> data reading
-> visual report
```

Main capabilities:

- CSV ingestion.
- Basic data quality checks.
- Electoral metrics calculation.
- Turnout and vote concentration analysis.
- Contextual comparison when comparable data is available.
- Guided dashboard.
- HTML report generation.
- Data reading with neutral interpretation.
- Automated tests.

## Tech stack

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Streamlit
- Jinja2
- Docker Compose
- pytest

## Requirements

- Docker Desktop
- Docker Compose
- Git

No local Python installation is required for Docker-based usage.

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

Open the application:

```text
Dashboard: http://localhost:8501
API docs:  http://localhost:8000/docs
Health:    http://localhost:8000/health
```

## Basic use

From the dashboard:

```text
Analizar -> Ejecutar demo
Analizar -> Generar lectura de datos
Analizar -> Generar reporte final
```

The final report includes:

- summary of the observed case,
- main atypical signals,
- data behavior reading,
- basic data quality notes,
- contextual comparison,
- charts,
- technical appendix.

## CSV format

For best results, the CSV should include fields equivalent to:

```text
department
municipality
polling_station
table_number
candidate or electoral option
party
votes
registered_voters
```

Different column names can be mapped with aliases in:

```text
config/column_aliases.yaml
```

## Interpretation

The report uses neutral language. A signal means that the data shows an atypical behavior compared with the available context. It does not prove fraud, intention, responsibility, or legal wrongdoing.

## Useful commands

Reset local environment:

```powershell
docker compose down -v
docker compose up --build
```

Run tests:

```powershell
docker compose exec api pytest
```

## Documentation

- [Project report](docs/project_report.md)
- [Video script](docs/video_script.md)
- [Setup](docs/setup.md)
- [Reports](docs/reports.md)
- [API](docs/api.md)
