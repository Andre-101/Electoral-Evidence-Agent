# Architecture

## Overview

```text
Streamlit Dashboard
        ↓
FastAPI API
        ↓
Application Services
        ↓
SQLAlchemy Models
        ↓
PostgreSQL
```

## Main services

| Service | Responsibility |
|---|---|
| `IngestionService` | Registers uploaded files and calculates file hashes. |
| `MappingService` | Maps source columns to canonical electoral fields. |
| `CoreLoadService` | Loads normalized data into electoral tables. |
| `QualityValidationService` | Creates quality alerts. |
| `MetricsService` | Calculates totals, metrics and territorial comparisons. |
| `AlertService` | Generates anomaly alerts. |
| `ScoringService` | Creates review scores and review cases. |
| `EvidenceService` | Builds structured evidence and agent context. |
| `AgentService` | Generates evidence dossiers with deterministic or optional Claude drafting. |
| `ReportService` | Exports case and executive reports as HTML. |
| `DemoService` | Runs the complete demo pipeline. |

## Processing flow

```text
CSV → profiling → mapping → core loading → quality → metrics → alerts → scoring → evidence → dossier → report
```
