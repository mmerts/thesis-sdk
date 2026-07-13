# -*- coding: utf-8 -*-
"""Create analysis charts from experiment data."""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Create figures directory
figures_dir = Path(__file__).parent / "figures"
figures_dir.mkdir(exist_ok=True)

# Data from MCP query
models = ['Haiku 3.0', 'Haiku 3.5', 'Haiku 4.5']
baseline_rates = [20.0, 18.8, 54.9]
reflexion_rates = [36.3, 42.5, 75.0]

# Chart 1: Model Comparison - Baseline vs Reflexion
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(models))
width = 0.35

bars1 = ax.bar(x - width/2, baseline_rates, width, label='Baseline', color='#3498db')
bars2 = ax.bar(x + width/2, reflexion_rates, width, label='Reflexion', color='#e74c3c')

ax.set_ylabel('Success Rate (%)', fontsize=12)
ax.set_xlabel('Model', fontsize=12)
ax.set_title('Baseline vs Reflexion Success Rate by Model', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(models)
ax.legend()
ax.set_ylim(0, 100)

# Add value labels on bars
for bar in bars1:
    height = bar.get_height()
    ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)
for bar in bars2:
    height = bar.get_height()
    ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig(figures_dir / '1_model_comparison.png', dpi=150)
plt.savefig(figures_dir / '1_model_comparison.pdf')
plt.close()
print("Chart 1: Model Comparison saved")

# Chart 2: Reflexion Lift (improvement)
fig, ax = plt.subplots(figsize=(10, 6))
lifts = [r - b for b, r in zip(baseline_rates, reflexion_rates)]
colors = ['#2ecc71' if l > 0 else '#e74c3c' for l in lifts]

bars = ax.bar(models, lifts, color=colors, edgecolor='black', linewidth=1.2)
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax.set_ylabel('Success Rate Improvement (%)', fontsize=12)
ax.set_xlabel('Model', fontsize=12)
ax.set_title('Reflexion Improvement Over Baseline', fontsize=14, fontweight='bold')

for bar in bars:
    height = bar.get_height()
    ax.annotate(f'+{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom',
                fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig(figures_dir / '2_reflexion_lift.png', dpi=150)
plt.savefig(figures_dir / '2_reflexion_lift.pdf')
plt.close()
print("Chart 2: Reflexion Lift saved")

# Chart 3: Case-by-Case Comparison
cases = ['Case 1\nWrong Port', 'Case 2\nImage Pull', 'Case 3\nResource', 'Case 4\nLiveness',
         'Case 5\nCommand', 'Case 6\nService', 'Case 7\nVolume', 'Case 8\nEnv Var']
baseline_case = [1/30*100, 14/30*100, 11/30*100, 10/30*100, 4/30*100, 24/30*100, 4/28*100, 2/23*100]
reflexion_case = [3/23*100, 5/23*100, 9/23*100, 6/23*100, 20/23*100, 22/23*100, 5/23*100, 11/23*100]

fig, ax = plt.subplots(figsize=(14, 7))
x = np.arange(len(cases))
width = 0.35

bars1 = ax.bar(x - width/2, baseline_case, width, label='Baseline', color='#3498db')
bars2 = ax.bar(x + width/2, reflexion_case, width, label='Reflexion', color='#e74c3c')

ax.set_ylabel('Success Rate (%)', fontsize=12)
ax.set_xlabel('Test Case', fontsize=12)
ax.set_title('Success Rate by Test Case: Baseline vs Reflexion', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(cases, fontsize=9)
ax.legend(loc='upper right')
ax.set_ylim(0, 110)

plt.tight_layout()
plt.savefig(figures_dir / '3_case_comparison.png', dpi=150)
plt.savefig(figures_dir / '3_case_comparison.pdf')
plt.close()
print("Chart 3: Case Comparison saved")

print(f"\nAll charts saved to: {figures_dir}")
