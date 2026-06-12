#!/bin/bash
# File: backend/app/db/scripts/run_next_7_days.sh
# Run this script from the same directory where download_matches.py resides.
# It will automatically pick the correct Python interpreter (python3 or python).

set -e

# --- Find Python command ----------------------------------------------------
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Neither python3 nor python found in PATH."
    exit 1
fi

# --- Ensure we are in the same directory as the script (optional) ----------
cd "$(dirname "$0")"

# --- Loop over today and the next 6 days -----------------------------------
today=$(date +%Y-%m-%d)

for i in {0..6}; do
    target_date=$(date -d "$today + $i days" +%Y-%m-%d)
    echo "=== Simulating games for $target_date ==="
    $PYTHON_CMD download_matches.py "$target_date"
done

echo "All done."