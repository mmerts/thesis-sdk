# -*- coding: utf-8 -*-
"""
Create SQLite database from JSON results for MCP integration.
"""

import json
import glob
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "results" / "results.db"
RESULTS_DIR = Path(__file__).parent.parent / "results" / "raw"

def create_tables(conn):
    """Create database tables."""
    conn.executescript("""
        DROP TABLE IF EXISTS experiments;
        DROP TABLE IF EXISTS trials;
        DROP TABLE IF EXISTS commands;

        CREATE TABLE experiments (
            id TEXT PRIMARY KEY,
            model TEXT,
            config TEXT,
            case_id TEXT,
            run_id INTEGER,
            success BOOLEAN,
            trials_used INTEGER,
            final_status TEXT,
            total_time REAL,
            total_cost REAL,
            total_tokens INTEGER,
            timestamp TEXT
        );

        CREATE TABLE trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            trial_num INTEGER,
            success BOOLEAN,
            pod_status TEXT,
            eval_reason TEXT,
            actor_time REAL,
            eval_time REAL,
            reflection_time REAL,
            actor_cost REAL,
            reflection_cost REAL,
            actor_input_tokens INTEGER,
            actor_output_tokens INTEGER,
            reflection_tokens INTEGER,
            trajectory TEXT,
            reflection_content TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id)
        );

        CREATE TABLE commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            trial_num INTEGER,
            command_order INTEGER,
            command TEXT,
            output TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id)
        );

        -- Useful views
        CREATE VIEW success_rates AS
        SELECT
            model,
            config,
            case_id,
            COUNT(*) as total_tests,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
            ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate
        FROM experiments
        GROUP BY model, config, case_id;

        CREATE VIEW model_summary AS
        SELECT
            model,
            config,
            COUNT(*) as total_tests,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
            ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate,
            ROUND(AVG(total_cost), 4) as avg_cost,
            ROUND(AVG(total_time), 1) as avg_time
        FROM experiments
        GROUP BY model, config;

        CREATE VIEW case_summary AS
        SELECT
            case_id,
            COUNT(*) as total_tests,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
            ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate,
            ROUND(AVG(total_time), 1) as avg_time
        FROM experiments
        GROUP BY case_id;

        CREATE VIEW reflexion_lift AS
        SELECT
            b.case_id,
            b.success_rate as baseline_rate,
            r.success_rate as reflexion_rate,
            ROUND(r.success_rate - b.success_rate, 1) as lift
        FROM
            (SELECT case_id, success_rate FROM success_rates WHERE config='baseline' GROUP BY case_id) b
        JOIN
            (SELECT case_id, success_rate FROM success_rates WHERE config='full_reflexion' GROUP BY case_id) r
        ON b.case_id = r.case_id;

        CREATE VIEW failure_reasons AS
        SELECT
            eval_reason,
            COUNT(*) as count
        FROM trials
        WHERE success = 0
        GROUP BY eval_reason
        ORDER BY count DESC;

        CREATE VIEW command_frequency AS
        SELECT
            CASE
                WHEN command LIKE 'kubectl get%' THEN 'kubectl get'
                WHEN command LIKE 'kubectl describe%' THEN 'kubectl describe'
                WHEN command LIKE 'kubectl logs%' THEN 'kubectl logs'
                WHEN command LIKE 'kubectl delete%' THEN 'kubectl delete'
                WHEN command LIKE 'kubectl apply%' THEN 'kubectl apply'
                WHEN command LIKE 'kubectl patch%' THEN 'kubectl patch'
                WHEN command LIKE 'kubectl run%' THEN 'kubectl run'
                WHEN command LIKE 'cat%' THEN 'cat/create file'
                ELSE 'other'
            END as command_type,
            COUNT(*) as count
        FROM commands
        GROUP BY command_type
        ORDER BY count DESC;
    """)

def load_results(conn):
    """Load all JSON results into database."""
    loaded = 0
    skipped = 0
    for model_dir in ["haiku30", "haiku35", "haiku45", "sonnet45", "opus45"]:
        # Collect files from both subfolders and directly in model folder
        files = glob.glob(str(RESULTS_DIR / model_dir / "**" / "*.json"), recursive=True)
        files += glob.glob(str(RESULTS_DIR / model_dir / "*.json"))
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  SKIP (invalid JSON): {filepath}")
                skipped += 1
                continue

            # Insert experiment (skip duplicates)
            conn.execute("""
                INSERT OR REPLACE INTO experiments (id, model, config, case_id, run_id, success,
                    trials_used, final_status, total_time, total_cost, total_tokens, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('experiment_id'),
                data.get('model'),
                data.get('config'),
                data.get('case_id'),
                data.get('run_id'),
                data.get('success'),
                data.get('trials_used'),
                data.get('final_status'),
                data.get('total_time'),
                data.get('total_cost'),
                data.get('total_tokens'),
                data.get('timestamp')
            ))

            # Insert trials
            for trial in data.get('trial_details', []):
                conn.execute("""
                    INSERT INTO trials (experiment_id, trial_num, success, pod_status,
                        eval_reason, actor_time, eval_time, reflection_time, actor_cost,
                        reflection_cost, actor_input_tokens, actor_output_tokens,
                        reflection_tokens, trajectory, reflection_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('experiment_id'),
                    trial.get('trial'),
                    trial.get('success'),
                    trial.get('pod_status'),
                    trial.get('eval_reason'),
                    trial.get('actor_time'),
                    trial.get('eval_time'),
                    trial.get('reflection_time'),
                    trial.get('actor_cost'),
                    trial.get('reflection_cost'),
                    trial.get('actor_input_tokens'),
                    trial.get('actor_output_tokens'),
                    trial.get('reflection_tokens'),
                    trial.get('trajectory'),
                    trial.get('reflection_content')
                ))

                # Insert commands
                for i, cmd in enumerate(trial.get('commands', [])):
                    conn.execute("""
                        INSERT INTO commands (experiment_id, trial_num, command_order, command, output)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        data.get('experiment_id'),
                        trial.get('trial'),
                        i + 1,
                        cmd.get('command'),
                        cmd.get('output')
                    ))

def main():
    print(f"Creating database at: {DB_PATH}")

    # Remove existing database
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    print("Creating tables...")
    create_tables(conn)

    print("Loading results...")
    load_results(conn)

    conn.commit()

    # Print summary
    cursor = conn.execute("SELECT COUNT(*) FROM experiments")
    exp_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM trials")
    trial_count = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM commands")
    cmd_count = cursor.fetchone()[0]

    print(f"\nDatabase created successfully!")
    print(f"  - Experiments: {exp_count}")
    print(f"  - Trials: {trial_count}")
    print(f"  - Commands: {cmd_count}")

    # Test a view
    print("\n--- Model Summary ---")
    for row in conn.execute("SELECT * FROM model_summary"):
        print(row)

    conn.close()
    print(f"\nDatabase saved to: {DB_PATH}")

if __name__ == "__main__":
    main()
