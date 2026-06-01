from sqlalchemy.orm import Session

from app.db.models.catalogs import (
    AlertCatalog,
    Country,
    ElectionType,
    OptionType,
    ResultType,
    SeverityCatalog,
)
from app.db.session import SessionLocal


def get_or_create(db: Session, model, defaults: dict | None = None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).one_or_none()
    if instance:
        return instance
    data = {**kwargs, **(defaults or {})}
    instance = model(**data)
    db.add(instance)
    db.flush()
    return instance


def seed() -> None:
    db = SessionLocal()
    try:
        get_or_create(db, Country, country_name="Colombia", iso_code="COL")

        for code in ["PRESIDENTIAL", "SENATE", "CHAMBER", "MAYOR", "GOVERNOR", "COUNCIL", "ASSEMBLY", "OTHER"]:
            get_or_create(db, ElectionType, code=code, defaults={"description": code})

        for code in ["PRECOUNT", "SCRUTINY", "HISTORICAL", "UNKNOWN"]:
            get_or_create(db, ResultType, code=code, defaults={"description": code})

        for code in ["CANDIDATE", "PARTY", "BLANK", "NULL", "UNMARKED", "OTHER"]:
            get_or_create(db, OptionType, code=code, defaults={"description": code})

        severities = {"LOW": 5, "MEDIUM": 15, "HIGH": 30, "CRITICAL": 50}
        for code, points in severities.items():
            get_or_create(db, SeverityCatalog, code=code, defaults={"points": points, "description": code})

        alerts = {
            "NEGATIVE_VOTES": ("QUALITY", "CRITICAL", "Votos negativos", "votes"),
            "INVALID_NUMERIC_VALUE": ("QUALITY", "HIGH", "Valor numérico inválido", "votes"),
            "MISSING_TABLE": ("QUALITY", "CRITICAL", "Mesa faltante", "table_number"),
            "MISSING_MUNICIPALITY": ("QUALITY", "HIGH", "Municipio faltante", "municipality"),
            "DUPLICATED_LOGICAL_RESULT": ("QUALITY", "HIGH", "Duplicado lógico", None),
            "VOTES_GREATER_THAN_CENSUS": ("QUALITY", "CRITICAL", "Votos mayores al censo", "total_votes"),
            "UNKNOWN_RESULT_TYPE": ("QUALITY", "MEDIUM", "Tipo de resultado desconocido", "result_type"),
            "UNMATCHED_MUNICIPALITY": ("QUALITY", "MEDIUM", "Municipio no mapeado", "municipality"),
            "TURNOUT_GT_100": ("TURNOUT", "CRITICAL", "Participación mayor a 100%", "turnout"),
            "TURNOUT_GE_95": ("TURNOUT", "HIGH", "Participación mayor o igual a 95%", "turnout"),
            "TURNOUT_LE_20": ("TURNOUT", "MEDIUM", "Participación menor o igual a 20%", "turnout"),
            "WINNER_SHARE_GE_95": ("CONCENTRATION", "HIGH", "Ganador mayor o igual a 95%", "winner_share"),
            "WINNER_SHARE_GE_90": ("CONCENTRATION", "MEDIUM", "Ganador mayor o igual a 90%", "winner_share"),
            "MARGIN_GE_80": ("CONCENTRATION", "HIGH", "Margen mayor o igual a 80%", "margin_rate"),
            "TABLE_TURNOUT_OUTLIER_STATION": ("TERRITORIAL", "HIGH", "Participación atípica vs puesto", "robust_z_turnout_station"),
            "TABLE_PARTY_SHARE_OUTLIER_STATION": ("TERRITORIAL", "HIGH", "Opción atípica vs puesto", "robust_z_party_share_station"),
            "TABLE_DIFF_STATION_GE_30PP": ("TERRITORIAL", "HIGH", "Diferencia >= 30 pp vs puesto", "diff_vs_station"),
            "TABLE_DIFF_STATION_GE_20PP": ("TERRITORIAL", "MEDIUM", "Diferencia >= 20 pp vs puesto", "diff_vs_station"),
        }
        for code, (category, severity, description, metric) in alerts.items():
            get_or_create(
                db,
                AlertCatalog,
                alert_code=code,
                defaults={
                    "category": category,
                    "default_severity": severity,
                    "description": description,
                    "metric_name": metric,
                },
            )

        db.commit()
        print("Catalog seeds completed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
