#!/usr/bin/env bash
set -e
alembic upgrade head
python db/seeds/seed_catalogs.py
python db/seeds/seed_pilot_election.py
