from pathlib import Path

from app.core.settings import load_yaml_config


def test_required_configs_load():
    for config_name in [
        "rules.yaml",
        "scoring.yaml",
        "elections.yaml",
        "agent_policy.yaml",
        "column_aliases.yaml",
    ]:
        data = load_yaml_config(Path("config") / config_name)
        assert "version" in data
        assert data["version"] == "0.1.0"


def test_scoring_uses_review_priority_score():
    data = load_yaml_config("config/scoring.yaml")
    assert data["score_name"] == "review_priority_score"
