# -*- coding: utf-8 -*-
"""Import missing experiment results from JSON files to database"""
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(__file__).parent.parent / "results" / "results.db"
RAW_PATH = Path(__file__).parent.parent / "results" / "raw"

def get_existing_experiments(conn):
    """Get set of existing experiment IDs from database"""
    cursor = conn.execute("SELECT id FROM experiments")
    return {row[0] for row in cursor.fetchall()}

def import_json_file(conn, filepath, existing_ids):
    """Import a single JSON file to database if not already exists"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    exp_id = data.get('experiment_id')
    if not exp_id:
        return None, "No experiment_id"

    if exp_id in existing_ids:
        return None, "Already exists"

    # Extract data
    model = data.get('model', '')
    config = data.get('config', '')
    case_id = data.get('case_id', '')
    run_id = data.get('run_id', 0)
    success = 1 if data.get('success', False) else 0
    trials_used = data.get('trials_used', 0)
    final_status = data.get('final_status', '')
    total_time = data.get('total_time', 0)
    total_cost = data.get('total_cost', 0)
    total_tokens = data.get('total_tokens', 0)
    timestamp = data.get('timestamp', datetime.now().isoformat())

    # Insert into database
    conn.execute("""
        INSERT INTO experiments
        (id, model, config, case_id, run_id, success, trials_used, final_status, total_time, total_cost, total_tokens, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (exp_id, model, config, case_id, run_id, success, trials_used, final_status, total_time, total_cost, total_tokens, timestamp))

    return exp_id, "Imported"

def main():
    conn = sqlite3.connect(DB_PATH)
    existing_ids = get_existing_experiments(conn)

    print(f"Database: {DB_PATH}")
    print(f"Existing experiments: {len(existing_ids)}")
    print("="*60)

    imported = 0
    skipped = 0
    errors = 0

    # Scan all JSON files in raw folder
    for model_dir in RAW_PATH.iterdir():
        if not model_dir.is_dir():
            continue

        model = model_dir.name

        # Check root level JSON files (power test results)
        for json_file in model_dir.glob("*.json"):
            try:
                exp_id, status = import_json_file(conn, json_file, existing_ids)
                if status == "Imported":
                    imported += 1
                    print(f"[+] {json_file.name}")
                    existing_ids.add(exp_id)
                elif status == "Already exists":
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"[!] Error: {json_file.name} - {e}")

        # Check case subfolders
        for case_dir in model_dir.iterdir():
            if not case_dir.is_dir():
                continue

            for config_dir in case_dir.iterdir():
                if not config_dir.is_dir():
                    continue

                for json_file in config_dir.glob("*.json"):
                    try:
                        exp_id, status = import_json_file(conn, json_file, existing_ids)
                        if status == "Imported":
                            imported += 1
                            print(f"[+] {model}/{case_dir.name}/{config_dir.name}/{json_file.name}")
                            existing_ids.add(exp_id)
                        elif status == "Already exists":
                            skipped += 1
                    except Exception as e:
                        errors += 1
                        print(f"[!] Error: {json_file.name} - {e}")

    conn.commit()
    conn.close()

    print("="*60)
    print(f"Imported: {imported}")
    print(f"Skipped (already exists): {skipped}")
    print(f"Errors: {errors}")
    print(f"Total in DB now: {len(existing_ids)}")

if __name__ == "__main__":
    main()
