#!/bin/bash
set -e

if [ ! -d "vector_db" ] || [ -z "$(ls -A vector_db 2>/dev/null)" ]; then
    echo "[START] Budowanie bazy wektorowej..."
    python implementation/ingest.py
    echo "[START] Baza wektorowa gotowa."
fi

exec python app.py
