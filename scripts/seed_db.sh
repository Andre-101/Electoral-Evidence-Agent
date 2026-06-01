#!/usr/bin/env bash
set -e
python db/seeds/seed_catalogs.py
python db/seeds/seed_pilot_election.py
