#!/usr/bin/env python3
"""Load all experiment JSON files into SQLite database."""

import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(__file__).parent.parent / "results.db"
RAW_DIRS = [
    Path(__file__).parent / "results" / "raw" / "haiku30",
    Path(__file__).parent / "results" / "raw" / "haiku35",
    Path(__file__).parent / "results" / "raw" / "haiku45",
]

# Also check nested structure
NESTED_DIRS = [
    Path(__file__).parent / "results" / "raw" / "haiku30",
    Path(__file__).parent / "results" / "raw" / "haiku35",
    Path(__file__).parent / "results" / "raw" / "haiku45",
]

def find_all_json_files():
    """Find all JSON result files."""
    files = []
    base = Path(__file__).parent.parent / "results" / "raw"

    # Search recursively
    for json_file in base.rglob("*.json"):
        files.append(json_file)

    return files

def parse_experiment_id(filename):
    """Parse model, config, case, run from filename."""
    # Format: haiku30_baseline_case1_run1_20251201_144424.json
    # or: haiku30_full_reflexion_case1_run1_20251201_144424.json
    # or: haiku30_two_try_no_reflection_case1_run1_20251201_144424.json
    name = filename.stem
    parts = name.split('_')

    model = parts[0]  # haiku30, haiku35, haiku45, sonnet45, opus45

    if 'baseline' in name:
        config = 'baseline'
        # haiku30_baseline_case1_run1_...
        case_idx = parts.index('baseline') + 1
    elif 'two_try_no_reflection' in name:
        config = 'two_try_no_reflection'
        # haiku30_two_try_no_reflection_case1_run1_...
        case_idx = parts.index('reflection') + 1
    else:
        config = 'full_reflexion'
        # haiku30_full_reflexion_case1_run1_...
        case_idx = parts.index('reflexion') + 1

    case_id = parts[case_idx]  # case1, case2, etc.
    run_part = parts[case_idx + 1]  # run1, run2, etc.
    run_id = int(run_part.replace('run', ''))

    experiment_id = f"{model}_{config}_{case_id}_run{run_id}"

    return {
        'id': experiment_id,
        'model': model,
        'config': config,
        'case_id': case_id,
        'run_id': run_id
    }

def load_json_file(filepath):
    """Load and parse a JSON result file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def insert_experiment(conn, exp_info, data):
    """Insert experiment record."""
    cursor = conn.cursor()

    # Extract summary data
    success = data.get('success', False)
    trials_used = data.get('trials_used', 0)
    final_status = data.get('final_status', 'unknown')
    total_time = data.get('total_time', 0.0)
    total_cost = data.get('total_cost', 0.0)
    total_tokens = data.get('total_tokens', 0)
    timestamp = data.get('timestamp', '')

    cursor.execute('''
        INSERT OR REPLACE INTO experiments
        (id, model, config, case_id, run_id, success, trials_used, final_status,
         total_time, total_cost, total_tokens, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        exp_info['id'], exp_info['model'], exp_info['config'],
        exp_info['case_id'], exp_info['run_id'],
        success, trials_used, final_status,
        total_time, total_cost, total_tokens, timestamp
    ))

    return cursor.lastrowid

def insert_trials(conn, experiment_id, trials_data):
    """Insert trial records."""
    cursor = conn.cursor()

    for trial in trials_data:
        trial_num = trial.get('trial', 0)
        success = trial.get('success', False)
        pod_status = trial.get('pod_status', '')
        eval_reason = trial.get('eval_reason', '') or trial.get('evaluation', {}).get('reason', '')

        # Time metrics
        actor_time = trial.get('actor_time', 0.0)
        eval_time = trial.get('eval_time', 0.0)
        reflection_time = trial.get('reflection_time', 0.0)

        # Cost metrics
        actor_cost = trial.get('actor_cost', 0.0)
        reflection_cost = trial.get('reflection_cost', 0.0)

        # Token metrics
        actor_input_tokens = trial.get('actor_input_tokens', 0)
        actor_output_tokens = trial.get('actor_output_tokens', 0)
        reflection_tokens = trial.get('reflection_tokens', 0)

        # Content
        trajectory = json.dumps(trial.get('trajectory', []))
        reflection_content = trial.get('reflection', '')

        cursor.execute('''
            INSERT INTO trials
            (experiment_id, trial_num, success, pod_status, eval_reason,
             actor_time, eval_time, reflection_time,
             actor_cost, reflection_cost,
             actor_input_tokens, actor_output_tokens, reflection_tokens,
             trajectory, reflection_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            experiment_id, trial_num, success, pod_status, eval_reason,
            actor_time, eval_time, reflection_time,
            actor_cost, reflection_cost,
            actor_input_tokens, actor_output_tokens, reflection_tokens,
            trajectory, reflection_content
        ))

def main():
    # Find all JSON files
    json_files = find_all_json_files()
    print(f"Found {len(json_files)} JSON files")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    loaded = 0
    errors = []

    for filepath in sorted(json_files):
        try:
            # Parse experiment info from filename
            exp_info = parse_experiment_id(filepath)

            # Load JSON data
            data = load_json_file(filepath)

            # Insert experiment
            insert_experiment(conn, exp_info, data)

            # Insert trials
            trials = data.get('trials', [])
            insert_trials(conn, exp_info['id'], trials)

            loaded += 1

        except Exception as e:
            errors.append((filepath.name, str(e)))
            print(f"Error loading {filepath.name}: {e}")

    conn.commit()
    conn.close()

    print(f"\nLoaded {loaded} experiments successfully")
    if errors:
        print(f"Errors: {len(errors)}")
        for name, err in errors[:5]:
            print(f"  - {name}: {err}")

if __name__ == "__main__":
    main()
