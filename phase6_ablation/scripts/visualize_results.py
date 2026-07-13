# -*- coding: utf-8 -*-
"""
Phase 6 Results Visualization
=============================
Creates publication-ready charts for the ablation study.
"""

import json
import glob
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Set style for publication
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 150

RESULTS_DIR = Path(__file__).parent / "results" / "raw"
OUTPUT_DIR = Path(__file__).parent / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)

# Case metadata
CASES = {
    "case1": {"name": "Wrong Port", "difficulty": "easy", "short": "C1"},
    "case2": {"name": "Incorrect Selector", "difficulty": "easy", "short": "C2"},
    "case3": {"name": "Liveness Probe", "difficulty": "medium", "short": "C3"},
    "case4": {"name": "Wrong Interface", "difficulty": "hard", "short": "C4"},
    "case5": {"name": "Port Mismatch", "difficulty": "hard", "short": "C5"},
    "case6": {"name": "Misspelling", "difficulty": "easy", "short": "C6"},
    "case7": {"name": "Volume Mount", "difficulty": "medium", "short": "C7"},
    "case8": {"name": "Environment Var", "difficulty": "medium", "short": "C8"},
}

MODELS = {
    "haiku30": "Haiku 3.0",
    "haiku35": "Haiku 3.5",
    "haiku45": "Haiku 4.5",
}

COLORS = {
    "haiku30": "#e74c3c",  # Red
    "haiku35": "#3498db",  # Blue
    "haiku45": "#2ecc71",  # Green
    "baseline": "#95a5a6",  # Gray
    "reflexion": "#9b59b6",  # Purple
}

def load_all_results():
    """Load all JSON result files."""
    results = []
    for model_dir in ["haiku30", "haiku35", "haiku45"]:
        pattern = str(RESULTS_DIR / model_dir / "**" / "*.json")
        for filepath in glob.glob(pattern, recursive=True):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
    return results

def calc_rate(successes):
    if not successes:
        return 0.0
    return sum(successes) / len(successes) * 100

def prepare_data(results):
    """Prepare grouped data for visualization."""
    by_model_config = defaultdict(list)
    by_case_config = defaultdict(list)
    by_model_case = defaultdict(list)

    for r in results:
        model = r.get('model', 'unknown')
        case = r.get('case_id', 'unknown')
        config = r.get('config', 'unknown')
        success = r.get('success', False)
        cost = r.get('total_cost', 0)
        time = r.get('total_time', 0)
        trials = r.get('trials_used', 1)

        by_model_config[(model, config)].append({
            'success': success, 'cost': cost, 'time': time, 'trials': trials
        })
        by_case_config[(case, config)].append({'success': success})
        by_model_case[(model, case)].append({'success': success})

    return by_model_config, by_case_config, by_model_case

def plot_model_comparison(by_model_config):
    """Plot 1: Model x Config comparison (grouped bar chart)."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = ["haiku30", "haiku35", "haiku45"]
    x = np.arange(len(models))
    width = 0.35

    baseline_rates = []
    reflexion_rates = []

    for model in models:
        baseline = by_model_config.get((model, "baseline"), [])
        reflexion = by_model_config.get((model, "full_reflexion"), [])
        baseline_rates.append(calc_rate([d['success'] for d in baseline]))
        reflexion_rates.append(calc_rate([d['success'] for d in reflexion]))

    bars1 = ax.bar(x - width/2, baseline_rates, width, label='Baseline (1 trial)',
                   color=COLORS['baseline'], edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, reflexion_rates, width, label='Reflexion (2 trials)',
                   color=COLORS['reflexion'], edgecolor='black', linewidth=0.5)

    # Add value labels
    for bar, rate in zip(bars1, baseline_rates):
        ax.annotate(f'{rate:.1f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                   xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=10)
    for bar, rate in zip(bars2, reflexion_rates):
        ax.annotate(f'{rate:.1f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                   xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=10)

    ax.set_xlabel('Model')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Success Rate by Model and Configuration')
    ax.set_xticks(x)
    ax.set_xticklabels([MODELS[m] for m in models])
    ax.legend(loc='upper left')
    ax.set_ylim(0, 100)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '1_model_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '1_model_comparison.pdf', bbox_inches='tight')
    print(f"Saved: 1_model_comparison.png/pdf")
    plt.close()

def plot_reflexion_lift(by_model_config):
    """Plot 2: Reflexion lift by model."""
    fig, ax = plt.subplots(figsize=(8, 5))

    models = ["haiku30", "haiku35", "haiku45"]
    lifts = []
    colors = []

    for model in models:
        baseline = by_model_config.get((model, "baseline"), [])
        reflexion = by_model_config.get((model, "full_reflexion"), [])
        b_rate = calc_rate([d['success'] for d in baseline])
        r_rate = calc_rate([d['success'] for d in reflexion])
        lifts.append(r_rate - b_rate)
        colors.append(COLORS[model])

    bars = ax.bar([MODELS[m] for m in models], lifts, color=colors, edgecolor='black', linewidth=0.5)

    for bar, lift in zip(bars, lifts):
        ax.annotate(f'+{lift:.1f}%', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                   xytext=(0, 3), textcoords='offset points', ha='center', va='bottom',
                   fontsize=12, fontweight='bold')

    ax.set_xlabel('Model')
    ax.set_ylabel('Reflexion Lift (percentage points)')
    ax.set_title('Improvement from Reflexion by Model')
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_ylim(0, 40)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '2_reflexion_lift.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '2_reflexion_lift.pdf', bbox_inches='tight')
    print(f"Saved: 2_reflexion_lift.png/pdf")
    plt.close()

def plot_case_comparison(by_case_config):
    """Plot 3: Success rate by case (grouped by difficulty)."""
    fig, ax = plt.subplots(figsize=(12, 6))

    cases = sorted(CASES.keys())
    x = np.arange(len(cases))
    width = 0.35

    baseline_rates = []
    reflexion_rates = []

    for case in cases:
        baseline = by_case_config.get((case, "baseline"), [])
        reflexion = by_case_config.get((case, "full_reflexion"), [])
        baseline_rates.append(calc_rate([d['success'] for d in baseline]))
        reflexion_rates.append(calc_rate([d['success'] for d in reflexion]))

    bars1 = ax.bar(x - width/2, baseline_rates, width, label='Baseline',
                   color=COLORS['baseline'], edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, reflexion_rates, width, label='Reflexion',
                   color=COLORS['reflexion'], edgecolor='black', linewidth=0.5)

    # Color-code by difficulty
    difficulty_colors = {'easy': '#27ae60', 'medium': '#f39c12', 'hard': '#c0392b'}
    for i, case in enumerate(cases):
        diff = CASES[case]['difficulty']
        ax.axvspan(i - 0.5, i + 0.5, alpha=0.1, color=difficulty_colors[diff])

    ax.set_xlabel('Test Case')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Success Rate by Test Case')

    # Custom x-axis labels
    labels = [f"{CASES[c]['short']}\n{CASES[c]['name']}\n({CASES[c]['difficulty']})" for c in cases]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '3_case_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '3_case_comparison.pdf', bbox_inches='tight')
    print(f"Saved: 3_case_comparison.png/pdf")
    plt.close()

def plot_reflexion_lift_by_case(by_case_config):
    """Plot 4: Reflexion lift by case."""
    fig, ax = plt.subplots(figsize=(10, 6))

    cases = sorted(CASES.keys())
    lifts = []
    colors = []
    difficulty_colors = {'easy': '#27ae60', 'medium': '#f39c12', 'hard': '#c0392b'}

    for case in cases:
        baseline = by_case_config.get((case, "baseline"), [])
        reflexion = by_case_config.get((case, "full_reflexion"), [])
        b_rate = calc_rate([d['success'] for d in baseline])
        r_rate = calc_rate([d['success'] for d in reflexion])
        lifts.append(r_rate - b_rate)
        colors.append(difficulty_colors[CASES[case]['difficulty']])

    bars = ax.bar([CASES[c]['short'] for c in cases], lifts, color=colors,
                  edgecolor='black', linewidth=0.5)

    for bar, lift, case in zip(bars, lifts, cases):
        ax.annotate(f'+{lift:.0f}%', xy=(bar.get_x() + bar.get_width()/2, max(lift, 0)),
                   xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=10)

    ax.set_xlabel('Test Case')
    ax.set_ylabel('Reflexion Lift (percentage points)')
    ax.set_title('Improvement from Reflexion by Test Case')
    ax.axhline(y=0, color='black', linewidth=0.5)

    # Legend for difficulty
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27ae60', label='Easy'),
        Patch(facecolor='#f39c12', label='Medium'),
        Patch(facecolor='#c0392b', label='Hard')
    ]
    ax.legend(handles=legend_elements, title='Difficulty', loc='upper right')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '4_reflexion_lift_by_case.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '4_reflexion_lift_by_case.pdf', bbox_inches='tight')
    print(f"Saved: 4_reflexion_lift_by_case.png/pdf")
    plt.close()

def plot_cost_vs_success(by_model_config):
    """Plot 5: Cost vs Success Rate scatter."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for model in ["haiku30", "haiku35", "haiku45"]:
        for config in ["baseline", "full_reflexion"]:
            data = by_model_config.get((model, config), [])
            if not data:
                continue

            avg_cost = np.mean([d['cost'] for d in data])
            success_rate = calc_rate([d['success'] for d in data])

            marker = 'o' if config == 'baseline' else 's'
            label = f"{MODELS[model]} ({'B' if config == 'baseline' else 'R'})"

            ax.scatter(avg_cost, success_rate, c=COLORS[model], marker=marker,
                      s=200, edgecolors='black', linewidths=1, label=label, alpha=0.8)

    ax.set_xlabel('Average Cost per Test ($)')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Cost-Effectiveness: Cost vs Success Rate')
    ax.legend(loc='lower right', fontsize=9)
    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '5_cost_vs_success.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '5_cost_vs_success.pdf', bbox_inches='tight')
    print(f"Saved: 5_cost_vs_success.png/pdf")
    plt.close()

def plot_trial_distribution(by_model_config):
    """Plot 6: Trial distribution for reflexion runs."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = ["haiku30", "haiku35", "haiku45"]
    x = np.arange(len(models))
    width = 0.25

    trial1_success = []
    trial2_success = []
    failed = []

    for model in models:
        data = by_model_config.get((model, "full_reflexion"), [])
        t1 = sum(1 for d in data if d['success'] and d['trials'] == 1)
        t2 = sum(1 for d in data if d['success'] and d['trials'] == 2)
        f = sum(1 for d in data if not d['success'])
        trial1_success.append(t1)
        trial2_success.append(t2)
        failed.append(f)

    bars1 = ax.bar(x - width, trial1_success, width, label='Success (Trial 1)', color='#2ecc71')
    bars2 = ax.bar(x, trial2_success, width, label='Success (Trial 2)', color='#3498db')
    bars3 = ax.bar(x + width, failed, width, label='Failed', color='#e74c3c')

    ax.set_xlabel('Model')
    ax.set_ylabel('Number of Tests')
    ax.set_title('Reflexion Trial Outcomes by Model')
    ax.set_xticks(x)
    ax.set_xticklabels([MODELS[m] for m in models])
    ax.legend()

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width()/2, height),
                           xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '6_trial_distribution.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '6_trial_distribution.pdf', bbox_inches='tight')
    print(f"Saved: 6_trial_distribution.png/pdf")
    plt.close()

def plot_heatmap(by_model_case):
    """Plot 7: Model x Case heatmap."""
    fig, ax = plt.subplots(figsize=(12, 5))

    models = ["haiku30", "haiku35", "haiku45"]
    cases = sorted(CASES.keys())

    data = np.zeros((len(models), len(cases)))

    for i, model in enumerate(models):
        for j, case in enumerate(cases):
            successes = by_model_case.get((model, case), [])
            data[i, j] = calc_rate([d['success'] for d in successes])

    im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

    # Labels
    ax.set_xticks(np.arange(len(cases)))
    ax.set_yticks(np.arange(len(models)))
    ax.set_xticklabels([f"{CASES[c]['short']}\n{CASES[c]['name']}" for c in cases], fontsize=9)
    ax.set_yticklabels([MODELS[m] for m in models])

    # Add text annotations
    for i in range(len(models)):
        for j in range(len(cases)):
            color = 'white' if data[i, j] < 50 else 'black'
            ax.text(j, i, f'{data[i, j]:.0f}%', ha='center', va='center', color=color, fontsize=10)

    ax.set_title('Success Rate Heatmap: Model x Case')
    plt.colorbar(im, ax=ax, label='Success Rate (%)')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '7_heatmap.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '7_heatmap.pdf', bbox_inches='tight')
    print(f"Saved: 7_heatmap.png/pdf")
    plt.close()

def plot_summary_dashboard(by_model_config, by_case_config):
    """Plot 8: Summary dashboard with multiple subplots."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Subplot 1: Model comparison
    ax1 = axes[0, 0]
    models = ["haiku30", "haiku35", "haiku45"]
    x = np.arange(len(models))
    width = 0.35

    baseline_rates = [calc_rate([d['success'] for d in by_model_config.get((m, "baseline"), [])]) for m in models]
    reflexion_rates = [calc_rate([d['success'] for d in by_model_config.get((m, "full_reflexion"), [])]) for m in models]

    ax1.bar(x - width/2, baseline_rates, width, label='Baseline', color=COLORS['baseline'])
    ax1.bar(x + width/2, reflexion_rates, width, label='Reflexion', color=COLORS['reflexion'])
    ax1.set_xticks(x)
    ax1.set_xticklabels([MODELS[m] for m in models])
    ax1.set_ylabel('Success Rate (%)')
    ax1.set_title('A) Success Rate by Model')
    ax1.legend()
    ax1.set_ylim(0, 100)

    # Subplot 2: Reflexion lift by model
    ax2 = axes[0, 1]
    lifts = [r - b for b, r in zip(baseline_rates, reflexion_rates)]
    bars = ax2.bar([MODELS[m] for m in models], lifts, color=[COLORS[m] for m in models])
    ax2.set_ylabel('Lift (percentage points)')
    ax2.set_title('B) Reflexion Improvement')
    for bar, lift in zip(bars, lifts):
        ax2.annotate(f'+{lift:.1f}%', xy=(bar.get_x() + bar.get_width()/2, lift),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10, fontweight='bold')

    # Subplot 3: Case comparison
    ax3 = axes[1, 0]
    cases = sorted(CASES.keys())
    case_rates = [calc_rate([d['success'] for d in by_case_config.get((c, "baseline"), []) +
                            by_case_config.get((c, "full_reflexion"), [])]) for c in cases]
    difficulty_colors = {'easy': '#27ae60', 'medium': '#f39c12', 'hard': '#c0392b'}
    colors = [difficulty_colors[CASES[c]['difficulty']] for c in cases]
    ax3.bar([CASES[c]['short'] for c in cases], case_rates, color=colors)
    ax3.set_ylabel('Success Rate (%)')
    ax3.set_title('C) Success Rate by Case')
    ax3.set_ylim(0, 100)

    # Subplot 4: Overall summary pie
    ax4 = axes[1, 1]
    total_baseline = sum(calc_rate([d['success'] for d in by_model_config.get((m, "baseline"), [])]) for m in models) / 3
    total_reflexion = sum(calc_rate([d['success'] for d in by_model_config.get((m, "full_reflexion"), [])]) for m in models) / 3

    ax4.bar(['Baseline\n(72 tests)', 'Reflexion\n(72 tests)'], [total_baseline, total_reflexion],
           color=[COLORS['baseline'], COLORS['reflexion']], edgecolor='black')
    ax4.set_ylabel('Avg Success Rate (%)')
    ax4.set_title('D) Overall Comparison')
    ax4.set_ylim(0, 100)

    for i, (rate, label) in enumerate([(total_baseline, 'Baseline'), (total_reflexion, 'Reflexion')]):
        ax4.annotate(f'{rate:.1f}%', xy=(i, rate), xytext=(0, 5),
                    textcoords='offset points', ha='center', fontsize=12, fontweight='bold')

    plt.suptitle('Phase 6 Ablation Study: Reflexion Framework for K8s Troubleshooting',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '8_summary_dashboard.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '8_summary_dashboard.pdf', bbox_inches='tight')
    print(f"Saved: 8_summary_dashboard.png/pdf")
    plt.close()

def plot_model_case_breakdown(results):
    """Plot 9: Model breakdown by case - grouped bar chart."""
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.flatten()

    cases = sorted(CASES.keys())
    models = ["haiku30", "haiku35", "haiku45"]

    for idx, case in enumerate(cases):
        ax = axes[idx]

        # Get data for this case
        baseline_rates = []
        reflexion_rates = []

        for model in models:
            baseline_success = []
            reflexion_success = []

            for r in results:
                if r.get('case_id') == case and r.get('model') == model:
                    if r.get('config') == 'baseline':
                        baseline_success.append(r.get('success', False))
                    else:
                        reflexion_success.append(r.get('success', False))

            baseline_rates.append(calc_rate(baseline_success))
            reflexion_rates.append(calc_rate(reflexion_success))

        x = np.arange(len(models))
        width = 0.35

        bars1 = ax.bar(x - width/2, baseline_rates, width, label='Baseline', color=COLORS['baseline'])
        bars2 = ax.bar(x + width/2, reflexion_rates, width, label='Reflexion', color=COLORS['reflexion'])

        ax.set_title(f"{CASES[case]['short']}: {CASES[case]['name']}\n({CASES[case]['difficulty']})", fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(['H3.0', 'H3.5', 'H4.5'], fontsize=9)
        ax.set_ylim(0, 100)

        if idx == 0:
            ax.legend(fontsize=8)
        if idx % 4 == 0:
            ax.set_ylabel('Success Rate (%)')

    plt.suptitle('Success Rate by Model for Each Case', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '9_model_case_breakdown.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '9_model_case_breakdown.pdf', bbox_inches='tight')
    print(f"Saved: 9_model_case_breakdown.png/pdf")
    plt.close()

def plot_baseline_vs_reflexion_cases(by_case_config):
    """Plot 10: Baseline vs Reflexion side-by-side for all cases."""
    fig, ax = plt.subplots(figsize=(14, 6))

    cases = sorted(CASES.keys())
    x = np.arange(len(cases))
    width = 0.35

    baseline_rates = []
    reflexion_rates = []

    for case in cases:
        baseline = by_case_config.get((case, "baseline"), [])
        reflexion = by_case_config.get((case, "full_reflexion"), [])
        baseline_rates.append(calc_rate([d['success'] for d in baseline]))
        reflexion_rates.append(calc_rate([d['success'] for d in reflexion]))

    bars1 = ax.bar(x - width/2, baseline_rates, width, label='Baseline (1 trial)',
                   color=COLORS['baseline'], edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, reflexion_rates, width, label='Reflexion (2 trials)',
                   color=COLORS['reflexion'], edgecolor='black', linewidth=0.5)

    # Add lift annotations
    for i, (b, r) in enumerate(zip(baseline_rates, reflexion_rates)):
        lift = r - b
        if lift > 0:
            ax.annotate(f'+{lift:.0f}%', xy=(i, max(b, r) + 3),
                       ha='center', fontsize=9, color='green', fontweight='bold')

    # Add value labels on bars
    for bar, rate in zip(bars1, baseline_rates):
        if rate > 0:
            ax.annotate(f'{rate:.0f}%', xy=(bar.get_x() + bar.get_width()/2, rate),
                       xytext=(0, 2), textcoords='offset points', ha='center', fontsize=8)
    for bar, rate in zip(bars2, reflexion_rates):
        if rate > 0:
            ax.annotate(f'{rate:.0f}%', xy=(bar.get_x() + bar.get_width()/2, rate),
                       xytext=(0, 2), textcoords='offset points', ha='center', fontsize=8)

    ax.set_xlabel('Test Case')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Baseline vs Reflexion: Success Rate Comparison by Case')

    labels = [f"{CASES[c]['short']}\n{CASES[c]['name']}" for c in cases]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 110)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '10_baseline_vs_reflexion_cases.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / '10_baseline_vs_reflexion_cases.pdf', bbox_inches='tight')
    print(f"Saved: 10_baseline_vs_reflexion_cases.png/pdf")
    plt.close()

def main():
    print("Loading results...")
    results = load_all_results()
    print(f"Loaded {len(results)} test results")

    print("\nPreparing data...")
    by_model_config, by_case_config, by_model_case = prepare_data(results)

    print("\nGenerating figures...")
    plot_model_comparison(by_model_config)
    plot_reflexion_lift(by_model_config)
    plot_case_comparison(by_case_config)
    plot_reflexion_lift_by_case(by_case_config)
    plot_cost_vs_success(by_model_config)
    plot_trial_distribution(by_model_config)
    plot_heatmap(by_model_case)
    plot_summary_dashboard(by_model_config, by_case_config)
    plot_model_case_breakdown(results)
    plot_baseline_vs_reflexion_cases(by_case_config)

    print(f"\nAll figures saved to: {OUTPUT_DIR}")
    print("Done!")

if __name__ == "__main__":
    main()
