# Configuration

Configuration is handled through `.env` and YAML files in `config/`.

## Main environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | SQLAlchemy database URL. |
| `UPLOAD_DIR` | Directory for uploaded files. |
| `PIPELINE_VERSION` | Pipeline version marker. |
| `RULES_VERSION` | Rules version marker. |
| `SCORING_VERSION` | Scoring version marker. |
| `ANTHROPIC_API_KEY` | Optional Claude API key. |
| `ANTHROPIC_MODEL` | Claude model configured by the operator. |
| `LLM_ENABLED` | `auto`, `true` or `false`. |
| `LLM_MAX_TOKENS` | Max tokens for Claude responses. |

## YAML files

| File | Purpose |
|---|---|
| `config/column_aliases.yaml` | Source column aliases. |
| `config/elections.yaml` | Pilot election metadata. |
| `config/rules.yaml` | Quality and anomaly rules. |
| `config/scoring.yaml` | Review scoring configuration. |
| `config/agent_policy.yaml` | Language policy for dossiers. |
