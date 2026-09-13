#!/usr/bin/env bash
set -e
python -m app.create_tables
python seed/seed_data.py
uvicorn app.main:app --host 0.0.0.0 --port $PORT
