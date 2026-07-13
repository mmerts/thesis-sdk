# -*- coding: utf-8 -*-
"""
Regenerate Figures with Correct Database Values
================================================
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Output directory
FIGURES_DIR = Path(__file__).parent.parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# =============================================================================
# CORRECT VALUES FROM DATABASE (verified)
# =============================================================================

# Model data (from database query)
MODELS = ['Haiku 3.0', 'Haiku 3.5', 'Haiku 4.5', 'Sonnet 4.5', 'Opus 4.5']
MODEL_BASELINE = [20.0, 18.75, 58.75, 61.25, 82.5]
MODEL_REFLEXION = [36.25, 42.5, 90.0, 85.0, 100.0]
MODEL_IMPROVEMENT = [r - b for b, r in zip(MODEL_BASELINE, MODEL_REFLEXION)]

# Case data (from database query)
CASES = [
    ('Case 1', 'Wrong Port'),
    ('Case 2', 'Incorrect Selector'),
    ('Case 3', 'Liveness Probe'),
    ('Case 4', 'Wrong Interface'),
    ('Case 5', 'Port Mismatch'),
    ('Case 6', 'Image Typo'),
    ('Case 7', 'Volume Mount'),
    ('Case 8', 'Environment Var'),
]
CASE_BASELINE = [24, 62, 56, 58, 36, 88, 10, 52]
CASE_REFLEXION = [52, 62, 72, 62, 94, 96, 52, 76]

# =============================================================================
# FIGURE 1: Model Comparison (5 models)
# =============================================================================
def create_figure1():
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(MODELS))
    width = 0.35

    bars1 = ax.bar(x - width/2, MODEL_BASELINE, width, label='Baseline', color='#3498db')
    bars2 = ax.bar(x + width/2, MODEL_REFLEXION, width, label='Reflexion', color='#e74c3c')

    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_xlabel('Model', fontsize=12)
    ax.set_title('Baseline vs Reflexion Success Rate by Model', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(MODELS)
    ax.legend()
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                   xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                   xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / '1_model_comparison.png', dpi=150, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / '1_model_comparison.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 1: Model Comparison saved")

# =============================================================================
# FIGURE 2: Reflexion Improvement (Lift)
# =============================================================================
def create_figure2():
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(MODELS))
    colors = ['#2ecc71' if imp > 0 else '#e74c3c' for imp in MODEL_IMPROVEMENT]

    bars = ax.bar(x, MODEL_IMPROVEMENT, color=colors, edgecolor='black', linewidth=1.5)

    ax.set_ylabel('Success Rate Improvement (pp)', fontsize=12)
    ax.set_xlabel('Model', fontsize=12)
    ax.set_title('Reflexion Improvement Over Baseline', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(MODELS)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'+{height:.1f}pp', xy=(bar.get_x() + bar.get_width()/2, height),
                   xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                   fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / '2_reflexion_lift.png', dpi=150, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / '2_reflexion_lift.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 2: Reflexion Lift saved")

# =============================================================================
# FIGURE 3: Case Comparison
# =============================================================================
def create_figure3():
    fig, ax = plt.subplots(figsize=(14, 6))

    x = np.arange(len(CASES))
    width = 0.35

    bars1 = ax.bar(x - width/2, CASE_BASELINE, width, label='Baseline', color='#3498db')
    bars2 = ax.bar(x + width/2, CASE_REFLEXION, width, label='Reflexion', color='#e74c3c')

    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_xlabel('Test Case', fontsize=12)
    ax.set_title('Success Rate by Test Case: Baseline vs Reflexion', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{c[0]}\n{c[1]}' for c in CASES], fontsize=9)
    ax.legend()
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / '3_case_comparison.png', dpi=150, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / '3_case_comparison.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 3: Case Comparison saved")

# =============================================================================
# FIGURE 4: Cost vs Success Rate (Scatter)
# =============================================================================
def create_figure4():
    # Cost data from database
    model_costs = {
        'Haiku 3.0': 0.05,
        'Haiku 3.5': 0.18,
        'Haiku 4.5': 0.19,
        'Sonnet 4.5': 0.53,
        'Opus 4.5': 0.90
    }

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, model in enumerate(MODELS):
        ax.scatter(model_costs[model], MODEL_REFLEXION[i], s=200, label=model, zorder=5)
        ax.annotate(model, (model_costs[model], MODEL_REFLEXION[i]),
                   xytext=(5, 5), textcoords='offset points', fontsize=9)

    ax.set_xlabel('Average Cost per Experiment ($)', fontsize=12)
    ax.set_ylabel('Reflexion Success Rate (%)', fontsize=12)
    ax.set_title('Cost-Effectiveness Analysis', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 110)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / '4_cost_effectiveness.png', dpi=150, bbox_inches='tight')
    plt.savefig(FIGURES_DIR / '4_cost_effectiveness.pdf', bbox_inches='tight')
    plt.close()
    print("✓ Figure 4: Cost Effectiveness saved")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("REGENERATING FIGURES WITH CORRECT DATABASE VALUES")
    print("="*60 + "\n")

    create_figure1()
    create_figure2()
    create_figure3()
    create_figure4()

    print("\n" + "="*60)
    print(f"All figures saved to: {FIGURES_DIR}")
    print("="*60 + "\n")
