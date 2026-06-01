from datetime import date

from sqlalchemy.orm import Session

from app.db.models.catalogs import Country, ElectionType, ResultType
from app.db.models.electoral_core import Election, Period
from app.db.session import SessionLocal


def get_one(db: Session, model, **kwargs):
    return db.query(model).filter_by(**kwargs).one()


def seed() -> None:
    db = SessionLocal()
    try:
        country = get_one(db, Country, iso_code="COL")
        election_type = get_one(db, ElectionType, code="PRESIDENTIAL")
        result_type = get_one(db, ResultType, code="SCRUTINY")

        period = db.query(Period).filter_by(
            country_id=country.country_id,
            year=2022,
            period_name="Elecciones Colombia 2022",
        ).one_or_none()
        if not period:
            period = Period(
                country_id=country.country_id,
                year=2022,
                period_name="Elecciones Colombia 2022",
            )
            db.add(period)
            db.flush()

        election = db.query(Election).filter_by(
            period_id=period.period_id,
            name="Colombia Presidencia 2022 - Primera vuelta - Escrutinio",
            result_type_id=result_type.result_type_id,
        ).one_or_none()

        if not election:
            election = Election(
                period_id=period.period_id,
                election_type_id=election_type.election_type_id,
                result_type_id=result_type.result_type_id,
                election_round=1,
                election_date=date(2022, 5, 29),
                name="Colombia Presidencia 2022 - Primera vuelta - Escrutinio",
                status="DRAFT",
                expected_analysis_level="TABLE_LEVEL",
            )
            db.add(election)

        db.commit()
        print("Pilot election seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
