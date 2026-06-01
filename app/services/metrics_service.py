from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from statistics import mean

from sqlalchemy.orm import Session

from app.analytics.robust_stats import mad_decimal, median_decimal, robust_z
from app.db.models.analytics import MunicipalityMetric, OptionTableMetric, StationMetric, TableMetric
from app.db.models.catalogs import OptionType
from app.db.models.control import IngestionRun
from app.db.models.electoral_core import ElectoralOption, PollingStation, PollingTable
from app.db.models.results import TableTotal, VoteResult


SPECIAL_OPTION_TYPES = {"BLANK", "NULL", "UNMARKED"}


def _safe_rate(numerator: int | float | Decimal | None, denominator: int | float | Decimal | None):
    if numerator is None or denominator in (None, 0):
        return None
    return Decimal(str(numerator)) / Decimal(str(denominator))


def _avg_decimal(values) -> Decimal | None:
    cleaned = [Decimal(str(v)) for v in values if v is not None]
    if not cleaned:
        return None
    return sum(cleaned) / Decimal(len(cleaned))


class MetricsService:
    def __init__(self, db: Session):
        self.db = db

    def _get_run(self, ingestion_run_id: uuid.UUID) -> IngestionRun:
        run = self.db.get(IngestionRun, ingestion_run_id)
        if run is None:
            raise ValueError(f"Ingestion run not found: {ingestion_run_id}")
        return run

    def _option_type_lookup(self) -> dict:
        option_types = {
            opt.option_type_id: opt.code for opt in self.db.query(OptionType).all()
        }
        electoral_options = {
            opt.electoral_option_id: opt for opt in self.db.query(ElectoralOption).all()
        }
        return {
            option_id: option_types.get(option.option_type_id)
            for option_id, option in electoral_options.items()
        }

    def calculate_table_totals(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self._get_run(ingestion_run_id)
        vote_results = (
            self.db.query(VoteResult)
            .filter(VoteResult.ingestion_run_id == ingestion_run_id)
            .all()
        )

        self.db.query(TableTotal).filter(
            TableTotal.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        by_table: dict[uuid.UUID, list[VoteResult]] = defaultdict(list)
        for result in vote_results:
            by_table[result.polling_table_id].append(result)

        option_type_by_option = self._option_type_lookup()

        created = 0
        for table_id, results in by_table.items():
            table = self.db.get(PollingTable, table_id)
            if table is None:
                continue

            total_votes = sum(r.votes for r in results)
            blank_votes = 0
            null_votes = 0
            unmarked_votes = 0

            for result in results:
                option_type = option_type_by_option.get(result.electoral_option_id)
                if option_type == "BLANK":
                    blank_votes += result.votes
                elif option_type == "NULL":
                    null_votes += result.votes
                elif option_type == "UNMARKED":
                    unmarked_votes += result.votes

            valid_votes = max(total_votes - blank_votes - null_votes - unmarked_votes, 0)

            table_total = TableTotal(
                election_id=table.election_id,
                polling_table_id=table.polling_table_id,
                registered_voters=table.registered_voters,
                total_votes=total_votes,
                valid_votes=valid_votes,
                blank_votes=blank_votes,
                null_votes=null_votes,
                unmarked_votes=unmarked_votes,
                option_count=len(results),
                ingestion_run_id=ingestion_run_id,
            )
            self.db.add(table_total)
            created += 1

        run.status = "METRICS_CALCULATED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "table_totals_created": created,
            "vote_results_used": len(vote_results),
        }

    def get_table_totals(self, ingestion_run_id: uuid.UUID) -> dict:
        totals = (
            self.db.query(TableTotal)
            .filter(TableTotal.ingestion_run_id == ingestion_run_id)
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [
                {
                    "table_total_id": str(item.table_total_id),
                    "polling_table_id": str(item.polling_table_id),
                    "registered_voters": item.registered_voters,
                    "total_votes": item.total_votes,
                    "valid_votes": item.valid_votes,
                    "blank_votes": item.blank_votes,
                    "null_votes": item.null_votes,
                    "unmarked_votes": item.unmarked_votes,
                    "option_count": item.option_count,
                }
                for item in totals
            ],
            "total": len(totals),
        }

    def _ensure_table_totals(self, ingestion_run_id: uuid.UUID) -> None:
        count = (
            self.db.query(TableTotal)
            .filter(TableTotal.ingestion_run_id == ingestion_run_id)
            .count()
        )
        if count == 0:
            self.calculate_table_totals(ingestion_run_id)

    def _ensure_basic_metrics(self, ingestion_run_id: uuid.UUID) -> None:
        table_count = (
            self.db.query(TableMetric)
            .filter(TableMetric.ingestion_run_id == ingestion_run_id)
            .count()
        )
        option_count = (
            self.db.query(OptionTableMetric)
            .filter(OptionTableMetric.ingestion_run_id == ingestion_run_id)
            .count()
        )
        if table_count == 0 or option_count == 0:
            self.calculate_all_basic_metrics(ingestion_run_id)

    def calculate_table_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self._get_run(ingestion_run_id)
        self._ensure_table_totals(ingestion_run_id)

        self.db.query(TableMetric).filter(
            TableMetric.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        totals = (
            self.db.query(TableTotal)
            .filter(TableTotal.ingestion_run_id == ingestion_run_id)
            .all()
        )
        vote_results = (
            self.db.query(VoteResult)
            .filter(VoteResult.ingestion_run_id == ingestion_run_id)
            .all()
        )
        by_table: dict[uuid.UUID, list[VoteResult]] = defaultdict(list)
        for result in vote_results:
            by_table[result.polling_table_id].append(result)

        option_type_by_option = self._option_type_lookup()
        created = 0

        for total in totals:
            results = by_table.get(total.polling_table_id, [])
            candidate_results = [
                result for result in results
                if option_type_by_option.get(result.electoral_option_id) not in SPECIAL_OPTION_TYPES
            ]
            sorted_results = sorted(candidate_results, key=lambda item: item.votes, reverse=True)

            winner = sorted_results[0] if sorted_results else None
            runner_up = sorted_results[1] if len(sorted_results) > 1 else None

            winner_votes = winner.votes if winner else None
            runner_up_votes = runner_up.votes if runner_up else None
            margin_votes = (
                winner_votes - runner_up_votes
                if winner_votes is not None and runner_up_votes is not None
                else None
            )

            metric = TableMetric(
                election_id=total.election_id,
                polling_table_id=total.polling_table_id,
                turnout=_safe_rate(total.total_votes, total.registered_voters),
                valid_vote_rate=_safe_rate(total.valid_votes, total.total_votes),
                blank_rate=_safe_rate(total.blank_votes, total.total_votes),
                null_rate=_safe_rate(total.null_votes, total.total_votes),
                unmarked_rate=_safe_rate(total.unmarked_votes, total.total_votes),
                winner_option_id=winner.electoral_option_id if winner else None,
                winner_votes=winner_votes,
                winner_share=_safe_rate(winner_votes, total.valid_votes),
                runner_up_votes=runner_up_votes,
                margin_votes=margin_votes,
                margin_rate=_safe_rate(margin_votes, total.valid_votes),
                ingestion_run_id=ingestion_run_id,
            )
            self.db.add(metric)
            created += 1

        run.status = "METRICS_CALCULATED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "table_metrics_created": created,
        }

    def calculate_option_table_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self._get_run(ingestion_run_id)
        self._ensure_table_totals(ingestion_run_id)

        self.db.query(OptionTableMetric).filter(
            OptionTableMetric.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        totals = {
            total.polling_table_id: total
            for total in self.db.query(TableTotal)
            .filter(TableTotal.ingestion_run_id == ingestion_run_id)
            .all()
        }
        vote_results = (
            self.db.query(VoteResult)
            .filter(VoteResult.ingestion_run_id == ingestion_run_id)
            .all()
        )

        created = 0
        for result in vote_results:
            total = totals.get(result.polling_table_id)
            if total is None:
                continue
            metric = OptionTableMetric(
                election_id=result.election_id,
                polling_table_id=result.polling_table_id,
                electoral_option_id=result.electoral_option_id,
                votes=result.votes,
                vote_share=_safe_rate(result.votes, total.valid_votes),
                diff_vs_station=None,
                diff_vs_municipality=None,
                robust_z_vs_station=None,
                robust_z_vs_municipality=None,
                ingestion_run_id=ingestion_run_id,
            )
            self.db.add(metric)
            created += 1

        run.status = "METRICS_CALCULATED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "option_table_metrics_created": created,
        }

    def calculate_all_basic_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        totals = self.calculate_table_totals(ingestion_run_id)
        table_metrics = self.calculate_table_metrics(ingestion_run_id)
        option_metrics = self.calculate_option_table_metrics(ingestion_run_id)
        return {
            "ingestion_run_id": str(ingestion_run_id),
            **totals,
            **table_metrics,
            **option_metrics,
        }

    def calculate_territorial_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self._get_run(ingestion_run_id)
        self._ensure_basic_metrics(ingestion_run_id)

        self.db.query(StationMetric).filter(
            StationMetric.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)
        self.db.query(MunicipalityMetric).filter(
            MunicipalityMetric.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        table_metrics = (
            self.db.query(TableMetric)
            .filter(TableMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        option_metrics = (
            self.db.query(OptionTableMetric)
            .filter(OptionTableMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        vote_results = (
            self.db.query(VoteResult)
            .filter(VoteResult.ingestion_run_id == ingestion_run_id)
            .all()
        )

        table_by_id = {
            table.polling_table_id: table
            for table in self.db.query(PollingTable).all()
        }
        station_by_table = {
            table_id: table.polling_station_election_id
            for table_id, table in table_by_id.items()
        }
        station_entity = {
            station.polling_station_id: station
            for station in self.db.query(PollingStation).all()
        }
        # polling_station_elections are not directly imported as a model here; use table station id only for station metrics.
        municipality_by_table = {}
        from app.db.models.electoral_core import PollingStationElection
        pse_by_id = {
            item.polling_station_election_id: item
            for item in self.db.query(PollingStationElection).all()
        }
        for table_id, station_election_id in station_by_table.items():
            pse = pse_by_id.get(station_election_id)
            if pse:
                station = station_entity.get(pse.polling_station_id)
                if station:
                    municipality_by_table[table_id] = station.municipality_id

        table_metric_by_table = {metric.polling_table_id: metric for metric in table_metrics}
        totals_by_table = {
            total.polling_table_id: total
            for total in self.db.query(TableTotal)
            .filter(TableTotal.ingestion_run_id == ingestion_run_id)
            .all()
        }

        # Station metrics
        table_metrics_by_station: dict[uuid.UUID, list[TableMetric]] = defaultdict(list)
        for metric in table_metrics:
            station_id = station_by_table.get(metric.polling_table_id)
            if station_id:
                table_metrics_by_station[station_id].append(metric)

        station_metrics_created = 0
        for station_id, metrics in table_metrics_by_station.items():
            turnouts = [metric.turnout for metric in metrics if metric.turnout is not None]
            median_turnout = median_decimal(turnouts)
            turnout_mad = mad_decimal(turnouts, median_turnout)
            total_votes = sum(totals_by_table[m.polling_table_id].total_votes for m in metrics if m.polling_table_id in totals_by_table)
            avg_turnout = _avg_decimal(turnouts)

            # Dominant option by votes in station.
            votes_by_option: dict[uuid.UUID, int] = defaultdict(int)
            for result in vote_results:
                if station_by_table.get(result.polling_table_id) == station_id:
                    votes_by_option[result.electoral_option_id] += result.votes
            dominant_option_id = None
            dominant_votes = 0
            if votes_by_option:
                dominant_option_id, dominant_votes = max(votes_by_option.items(), key=lambda item: item[1])
            dominant_share = _safe_rate(dominant_votes, total_votes)

            station_metric = StationMetric(
                election_id=metrics[0].election_id,
                polling_station_election_id=station_id,
                total_tables=len(metrics),
                total_votes=total_votes,
                average_turnout=avg_turnout,
                median_turnout=median_turnout,
                turnout_mad=turnout_mad,
                dominant_option_id=dominant_option_id,
                dominant_option_share=dominant_share,
                ingestion_run_id=ingestion_run_id,
            )
            self.db.add(station_metric)
            station_metrics_created += 1

        # Municipality metrics
        table_metrics_by_municipality: dict[uuid.UUID, list[TableMetric]] = defaultdict(list)
        for metric in table_metrics:
            municipality_id = municipality_by_table.get(metric.polling_table_id)
            if municipality_id:
                table_metrics_by_municipality[municipality_id].append(metric)

        municipality_metrics_created = 0
        for municipality_id, metrics in table_metrics_by_municipality.items():
            turnouts = [metric.turnout for metric in metrics if metric.turnout is not None]
            total_votes = sum(totals_by_table[m.polling_table_id].total_votes for m in metrics if m.polling_table_id in totals_by_table)
            avg_turnout = _avg_decimal(turnouts)
            median_turnout = median_decimal(turnouts)

            station_ids = {station_by_table.get(m.polling_table_id) for m in metrics if station_by_table.get(m.polling_table_id)}
            votes_by_option: dict[uuid.UUID, int] = defaultdict(int)
            for result in vote_results:
                if municipality_by_table.get(result.polling_table_id) == municipality_id:
                    votes_by_option[result.electoral_option_id] += result.votes
            dominant_option_id = None
            dominant_votes = 0
            if votes_by_option:
                dominant_option_id, dominant_votes = max(votes_by_option.items(), key=lambda item: item[1])
            dominant_share = _safe_rate(dominant_votes, total_votes)

            municipality_metric = MunicipalityMetric(
                election_id=metrics[0].election_id,
                municipality_id=municipality_id,
                total_stations=len(station_ids),
                total_tables=len(metrics),
                total_votes=total_votes,
                average_turnout=avg_turnout,
                median_turnout=median_turnout,
                dominant_option_id=dominant_option_id,
                dominant_option_share=dominant_share,
                ingestion_run_id=ingestion_run_id,
            )
            self.db.add(municipality_metric)
            municipality_metrics_created += 1

        # Update robust_z for table turnout is computed in AlertService, while option metrics persist option comparisons.
        option_metrics_by_station_option: dict[tuple[uuid.UUID, uuid.UUID], list[OptionTableMetric]] = defaultdict(list)
        option_metrics_by_municipality_option: dict[tuple[uuid.UUID, uuid.UUID], list[OptionTableMetric]] = defaultdict(list)

        for metric in option_metrics:
            station_id = station_by_table.get(metric.polling_table_id)
            municipality_id = municipality_by_table.get(metric.polling_table_id)
            if station_id:
                option_metrics_by_station_option[(station_id, metric.electoral_option_id)].append(metric)
            if municipality_id:
                option_metrics_by_municipality_option[(municipality_id, metric.electoral_option_id)].append(metric)

        updated_option_metrics = 0
        for metric in option_metrics:
            station_id = station_by_table.get(metric.polling_table_id)
            municipality_id = municipality_by_table.get(metric.polling_table_id)

            if station_id:
                group = option_metrics_by_station_option[(station_id, metric.electoral_option_id)]
                values = [item.vote_share for item in group if item.vote_share is not None]
                if len(values) >= 5:
                    center = median_decimal(values)
                    mad = mad_decimal(values, center)
                    rz = robust_z(metric.vote_share, center, mad)
                    metric.diff_vs_station = Decimal(str(metric.vote_share)) - center if metric.vote_share is not None and center is not None else None
                    metric.robust_z_vs_station = rz

            if municipality_id:
                group = option_metrics_by_municipality_option[(municipality_id, metric.electoral_option_id)]
                values = [item.vote_share for item in group if item.vote_share is not None]
                if len(values) >= 5:
                    center = median_decimal(values)
                    mad = mad_decimal(values, center)
                    rz = robust_z(metric.vote_share, center, mad)
                    metric.diff_vs_municipality = Decimal(str(metric.vote_share)) - center if metric.vote_share is not None and center is not None else None
                    metric.robust_z_vs_municipality = rz

            updated_option_metrics += 1

        run.status = "TERRITORIAL_METRICS_CALCULATED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "station_metrics_created": station_metrics_created,
            "municipality_metrics_created": municipality_metrics_created,
            "option_table_metrics_updated": updated_option_metrics,
        }

    def get_station_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        metrics = (
            self.db.query(StationMetric)
            .filter(StationMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [
                {
                    "station_metric_id": str(item.station_metric_id),
                    "polling_station_election_id": str(item.polling_station_election_id),
                    "total_tables": item.total_tables,
                    "total_votes": item.total_votes,
                    "average_turnout": float(item.average_turnout) if item.average_turnout is not None else None,
                    "median_turnout": float(item.median_turnout) if item.median_turnout is not None else None,
                    "turnout_mad": float(item.turnout_mad) if item.turnout_mad is not None else None,
                    "dominant_option_id": str(item.dominant_option_id) if item.dominant_option_id else None,
                    "dominant_option_share": float(item.dominant_option_share) if item.dominant_option_share is not None else None,
                }
                for item in metrics
            ],
            "total": len(metrics),
        }

    def get_municipality_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        metrics = (
            self.db.query(MunicipalityMetric)
            .filter(MunicipalityMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [
                {
                    "municipality_metric_id": str(item.municipality_metric_id),
                    "municipality_id": str(item.municipality_id),
                    "total_stations": item.total_stations,
                    "total_tables": item.total_tables,
                    "total_votes": item.total_votes,
                    "average_turnout": float(item.average_turnout) if item.average_turnout is not None else None,
                    "median_turnout": float(item.median_turnout) if item.median_turnout is not None else None,
                    "dominant_option_id": str(item.dominant_option_id) if item.dominant_option_id else None,
                    "dominant_option_share": float(item.dominant_option_share) if item.dominant_option_share is not None else None,
                }
                for item in metrics
            ],
            "total": len(metrics),
        }

    def get_table_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        metrics = (
            self.db.query(TableMetric)
            .filter(TableMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [
                {
                    "table_metric_id": str(item.table_metric_id),
                    "polling_table_id": str(item.polling_table_id),
                    "turnout": float(item.turnout) if item.turnout is not None else None,
                    "valid_vote_rate": float(item.valid_vote_rate) if item.valid_vote_rate is not None else None,
                    "blank_rate": float(item.blank_rate) if item.blank_rate is not None else None,
                    "null_rate": float(item.null_rate) if item.null_rate is not None else None,
                    "unmarked_rate": float(item.unmarked_rate) if item.unmarked_rate is not None else None,
                    "winner_option_id": str(item.winner_option_id) if item.winner_option_id else None,
                    "winner_votes": item.winner_votes,
                    "winner_share": float(item.winner_share) if item.winner_share is not None else None,
                    "runner_up_votes": item.runner_up_votes,
                    "margin_votes": item.margin_votes,
                    "margin_rate": float(item.margin_rate) if item.margin_rate is not None else None,
                }
                for item in metrics
            ],
            "total": len(metrics),
        }

    def get_option_table_metrics(self, ingestion_run_id: uuid.UUID) -> dict:
        metrics = (
            self.db.query(OptionTableMetric)
            .filter(OptionTableMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [
                {
                    "option_table_metric_id": str(item.option_table_metric_id),
                    "polling_table_id": str(item.polling_table_id),
                    "electoral_option_id": str(item.electoral_option_id),
                    "votes": item.votes,
                    "vote_share": float(item.vote_share) if item.vote_share is not None else None,
                    "diff_vs_station": float(item.diff_vs_station) if item.diff_vs_station is not None else None,
                    "diff_vs_municipality": float(item.diff_vs_municipality) if item.diff_vs_municipality is not None else None,
                    "robust_z_vs_station": float(item.robust_z_vs_station) if item.robust_z_vs_station is not None else None,
                    "robust_z_vs_municipality": float(item.robust_z_vs_municipality) if item.robust_z_vs_municipality is not None else None,
                }
                for item in metrics
            ],
            "total": len(metrics),
        }
