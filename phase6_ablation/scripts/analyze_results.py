# -*- coding: utf-8 -*-
"""
Phase 6 Results Analyzer
========================
Analyzes 144 test results across 3 models, 8 cases, 2 configs, 3 runs.
"""

import json
import glob
from pathlib import Path
from collections import defaultdict
import statistics

RESULTS_DIR = Path(__file__).parent / "results" / "raw"

# Case metadata
CASES = {
    "case1": {"name": "Wrong Port", "difficulty": "easy"},
    "case2": {"name": "Incorrect Selector", "difficulty": "easy"},
    "case3": {"name": "Liveness Probe", "difficulty": "medium"},
    "case4": {"name": "Wrong Interface", "difficulty": "hard"},
    "case5": {"name": "Port Mismatch", "difficulty": "hard"},
    "case6": {"name": "Misspelling", "difficulty": "easy"},
    "case7": {"name": "Volume Mount", "difficulty": "medium"},
    "case8": {"name": "Environment Variable", "difficulty": "medium"},
}

MODELS = {
    "haiku30": "Haiku 3.0",
    "haiku35": "Haiku 3.5",
    "haiku45": "Haiku 4.5",
}

def load_all_results():
    """Load all JSON result files."""
    results = []
    for model_dir in ["haiku30", "haiku35", "haiku45"]:
        pattern = str(RESULTS_DIR / model_dir / "**" / "*.json")
        for filepath in glob.glob(pattern, recursive=True):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['filepath'] = filepath
                results.append(data)
    return results

def analyze_success_rates(results):
    """Calculate success rates by model, case, and config."""

    # Group results
    by_model = defaultdict(list)
    by_case = defaultdict(list)
    by_config = defaultdict(list)
    by_model_config = defaultdict(list)
    by_model_case = defaultdict(list)
    by_case_config = defaultdict(list)

    for r in results:
        model = r.get('model', 'unknown')
        case = r.get('case_id', 'unknown')
        config = r.get('config', 'unknown')
        success = r.get('success', False)

        by_model[model].append(success)
        by_case[case].append(success)
        by_config[config].append(success)
        by_model_config[(model, config)].append(success)
        by_model_case[(model, case)].append(success)
        by_case_config[(case, config)].append(success)

    return {
        'by_model': by_model,
        'by_case': by_case,
        'by_config': by_config,
        'by_model_config': by_model_config,
        'by_model_case': by_model_case,
        'by_case_config': by_case_config,
    }

def calc_rate(successes):
    """Calculate success rate from list of booleans."""
    if not successes:
        return 0.0
    return sum(successes) / len(successes) * 100

def print_summary_tables(grouped):
    """Print summary tables."""

    print("\n" + "="*70)
    print("PHASE 6 ABLATION STUDY - RESULTS ANALYSIS")
    print("="*70)

    # 1. Overall by Model
    print("\n## 1. Success Rate by Model\n")
    print(f"{'Model':<15} {'Success':<10} {'Total':<10} {'Rate':<10}")
    print("-" * 45)
    for model in ["haiku30", "haiku35", "haiku45"]:
        successes = grouped['by_model'].get(model, [])
        rate = calc_rate(successes)
        print(f"{MODELS.get(model, model):<15} {sum(successes):<10} {len(successes):<10} {rate:.1f}%")

    # 2. Overall by Config
    print("\n## 2. Success Rate by Config\n")
    print(f"{'Config':<20} {'Success':<10} {'Total':<10} {'Rate':<10}")
    print("-" * 50)
    for config in ["baseline", "full_reflexion"]:
        successes = grouped['by_config'].get(config, [])
        rate = calc_rate(successes)
        label = "Baseline (1 trial)" if config == "baseline" else "Reflexion (2 trials)"
        print(f"{label:<20} {sum(successes):<10} {len(successes):<10} {rate:.1f}%")

    # 3. Model x Config Matrix
    print("\n## 3. Model x Config Success Rates\n")
    print(f"{'Model':<15} {'Baseline':<15} {'Reflexion':<15} {'Lift':<10}")
    print("-" * 55)
    for model in ["haiku30", "haiku35", "haiku45"]:
        baseline = grouped['by_model_config'].get((model, "baseline"), [])
        reflexion = grouped['by_model_config'].get((model, "full_reflexion"), [])
        b_rate = calc_rate(baseline)
        r_rate = calc_rate(reflexion)
        lift = r_rate - b_rate
        print(f"{MODELS.get(model, model):<15} {b_rate:>6.1f}%        {r_rate:>6.1f}%        {lift:>+5.1f}%")

    # 4. Success Rate by Case
    print("\n## 4. Success Rate by Case\n")
    print(f"{'Case':<8} {'Name':<20} {'Difficulty':<12} {'Rate':<10}")
    print("-" * 55)
    for case_id in sorted(CASES.keys()):
        successes = grouped['by_case'].get(case_id, [])
        rate = calc_rate(successes)
        info = CASES.get(case_id, {})
        print(f"{case_id:<8} {info.get('name', 'Unknown'):<20} {info.get('difficulty', '?'):<12} {rate:.1f}%")

    # 5. Case x Config (Reflexion Effect by Case)
    print("\n## 5. Reflexion Effect by Case\n")
    print(f"{'Case':<8} {'Baseline':<12} {'Reflexion':<12} {'Lift':<8} {'Difficulty':<10}")
    print("-" * 55)
    for case_id in sorted(CASES.keys()):
        baseline = grouped['by_case_config'].get((case_id, "baseline"), [])
        reflexion = grouped['by_case_config'].get((case_id, "full_reflexion"), [])
        b_rate = calc_rate(baseline)
        r_rate = calc_rate(reflexion)
        lift = r_rate - b_rate
        diff = CASES.get(case_id, {}).get('difficulty', '?')
        print(f"{case_id:<8} {b_rate:>5.1f}%       {r_rate:>5.1f}%       {lift:>+5.1f}%  {diff:<10}")

def analyze_costs_and_timing(results):
    """Analyze costs and timing."""

    print("\n## 6. Cost & Timing Analysis\n")

    by_model_config = defaultdict(list)
    for r in results:
        model = r.get('model', 'unknown')
        config = r.get('config', 'unknown')
        cost = r.get('total_cost', 0)
        time = r.get('total_time', 0)
        by_model_config[(model, config)].append({
            'cost': cost,
            'time': time,
            'success': r.get('success', False)
        })

    print(f"{'Model':<12} {'Config':<15} {'Avg Cost':<12} {'Avg Time':<12} {'Success Cost':<12}")
    print("-" * 65)

    for model in ["haiku30", "haiku35", "haiku45"]:
        for config in ["baseline", "full_reflexion"]:
            data = by_model_config.get((model, config), [])
            if not data:
                continue

            avg_cost = statistics.mean([d['cost'] for d in data])
            avg_time = statistics.mean([d['time'] for d in data])

            # Cost per success
            successes = [d for d in data if d['success']]
            success_cost = statistics.mean([d['cost'] for d in successes]) if successes else 0

            config_label = "baseline" if config == "baseline" else "reflexion"
            print(f"{MODELS.get(model, model):<12} {config_label:<15} ${avg_cost:<11.4f} {avg_time:<11.1f}s ${success_cost:.4f}")

def analyze_reflexion_trials(results):
    """Analyze how many trials reflexion uses."""

    print("\n## 7. Reflexion Trial Analysis\n")

    reflexion_results = [r for r in results if r.get('config') == 'full_reflexion']

    by_model = defaultdict(list)
    for r in reflexion_results:
        model = r.get('model', 'unknown')
        trials = r.get('trials_used', 1)
        success = r.get('success', False)
        by_model[model].append({'trials': trials, 'success': success})

    print(f"{'Model':<15} {'1-Trial Win':<12} {'2-Trial Win':<12} {'Failed':<10}")
    print("-" * 50)

    for model in ["haiku30", "haiku35", "haiku45"]:
        data = by_model.get(model, [])
        one_trial = sum(1 for d in data if d['success'] and d['trials'] == 1)
        two_trial = sum(1 for d in data if d['success'] and d['trials'] == 2)
        failed = sum(1 for d in data if not d['success'])
        print(f"{MODELS.get(model, model):<15} {one_trial:<12} {two_trial:<12} {failed:<10}")

def find_interesting_patterns(results):
    """Find interesting patterns in results."""

    print("\n## 8. Interesting Findings\n")

    # Cases where reflexion helped (baseline fail, reflexion success)
    reflexion_saved = []
    for r in results:
        if r.get('config') != 'full_reflexion' or not r.get('success'):
            continue

        # Find corresponding baseline
        model = r.get('model')
        case = r.get('case_id')
        run = r.get('run_id')

        for base in results:
            if (base.get('config') == 'baseline' and
                base.get('model') == model and
                base.get('case_id') == case and
                base.get('run_id') == run and
                not base.get('success')):
                reflexion_saved.append({
                    'model': model,
                    'case': case,
                    'run': run,
                    'trials': r.get('trials_used', 1)
                })

    print(f"### Cases where Reflexion saved the day ({len(reflexion_saved)} instances):\n")
    by_model = defaultdict(list)
    for item in reflexion_saved:
        by_model[item['model']].append(item)

    for model in ["haiku30", "haiku35", "haiku45"]:
        items = by_model.get(model, [])
        if items:
            cases = [f"{i['case']} (run {i['run']})" for i in items]
            print(f"- {MODELS.get(model, model)}: {', '.join(cases)}")

    # Outliers (very long runs)
    print("\n### Timing Outliers (>300s):\n")
    outliers = [r for r in results if r.get('total_time', 0) > 300]
    outliers.sort(key=lambda x: x.get('total_time', 0), reverse=True)
    for o in outliers[:5]:
        print(f"- {o.get('experiment_id', 'unknown')}: {o.get('total_time', 0):.0f}s")

def generate_latex_tables(grouped, results):
    """Generate LaTeX tables for paper."""

    print("\n" + "="*70)
    print("LATEX TABLES FOR PAPER")
    print("="*70)

    # Table 1: Model x Config
    print("\n% Table: Model vs Config Success Rates")
    print("\\begin{table}[h]")
    print("\\centering")
    print("\\begin{tabular}{lccc}")
    print("\\hline")
    print("Model & Baseline & Reflexion & Lift \\\\")
    print("\\hline")

    for model in ["haiku30", "haiku35", "haiku45"]:
        baseline = grouped['by_model_config'].get((model, "baseline"), [])
        reflexion = grouped['by_model_config'].get((model, "full_reflexion"), [])
        b_rate = calc_rate(baseline)
        r_rate = calc_rate(reflexion)
        lift = r_rate - b_rate
        print(f"{MODELS.get(model, model)} & {b_rate:.1f}\\% & {r_rate:.1f}\\% & +{lift:.1f}\\% \\\\")

    print("\\hline")
    print("\\end{tabular}")
    print("\\caption{Success rates by model and configuration}")
    print("\\label{tab:model-config}")
    print("\\end{table}")

def main():
    print("Loading results...")
    results = load_all_results()
    print(f"Loaded {len(results)} test results")

    grouped = analyze_success_rates(results)
    print_summary_tables(grouped)
    analyze_costs_and_timing(results)
    analyze_reflexion_trials(results)
    find_interesting_patterns(results)
    generate_latex_tables(grouped, results)

    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)

if __name__ == "__main__":
    main()
