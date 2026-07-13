"""
Case bazli sure analizi - Model karsilastirma grafigi
"""

import sqlite3
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).parent / "results.db"
FIGURES_PATH = Path(__file__).parent / "figures"

def main():
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        model,
        case_id,
        config,
        AVG(total_time) as avg_time
    FROM experiments
    GROUP BY model, case_id, config
    ORDER BY model, case_id, config
    """

    results = conn.execute(query).fetchall()
    conn.close()

    # Veriyi organize et
    models = ['haiku30', 'haiku35', 'haiku45']
    cases = [f'case{i}' for i in range(1, 9)]
    configs = ['baseline', 'full_reflexion']

    # Data dict
    data = {}
    for model, case_id, config, avg_time in results:
        key = (model, case_id, config)
        data[key] = avg_time

    # Figure 11: Model bazli case sureleri (grouped bar)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    x = np.arange(len(cases))
    width = 0.35

    model_names = {'haiku30': 'Haiku 3.0', 'haiku35': 'Haiku 3.5', 'haiku45': 'Haiku 4.5'}

    for idx, model in enumerate(models):
        ax = axes[idx]

        baseline_times = [data.get((model, case, 'baseline'), 0) for case in cases]
        reflexion_times = [data.get((model, case, 'full_reflexion'), 0) for case in cases]

        bars1 = ax.bar(x - width/2, baseline_times, width, label='Baseline', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, reflexion_times, width, label='Reflexion', color='#e74c3c', alpha=0.8)

        ax.set_xlabel('Case', fontsize=11)
        ax.set_ylabel('Avg Time (seconds)', fontsize=11)
        ax.set_title(f'{model_names[model]}', fontsize=13, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'C{i}' for i in range(1, 9)])
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(axis='y', alpha=0.3)

        # En uzun case'i vurgula
        max_time = max(reflexion_times)
        max_idx = reflexion_times.index(max_time)
        ax.annotate(f'{max_time:.0f}s',
                   xy=(max_idx + width/2, max_time),
                   ha='center', va='bottom',
                   fontsize=9, fontweight='bold', color='#c0392b')

    plt.suptitle('Average Execution Time by Case and Model', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    plt.savefig(FIGURES_PATH / 'fig11_time_by_case_model.png', dpi=150, bbox_inches='tight')
    plt.savefig(FIGURES_PATH / 'fig11_time_by_case_model.pdf', bbox_inches='tight')
    print("Saved: fig11_time_by_case_model.png/pdf")

    # Figure 12: En uzun sureli case'ler (heatmap style)
    fig, ax = plt.subplots(figsize=(10, 6))

    # Reflexion sureleri matrix
    time_matrix = np.zeros((len(models), len(cases)))
    for i, model in enumerate(models):
        for j, case in enumerate(cases):
            time_matrix[i, j] = data.get((model, case, 'full_reflexion'), 0)

    im = ax.imshow(time_matrix, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(np.arange(len(cases)))
    ax.set_yticks(np.arange(len(models)))
    ax.set_xticklabels([f'Case {i}' for i in range(1, 9)])
    ax.set_yticklabels([model_names[m] for m in models])

    # Degerleri goster
    for i in range(len(models)):
        for j in range(len(cases)):
            text = ax.text(j, i, f'{time_matrix[i, j]:.0f}s',
                          ha='center', va='center', color='black', fontsize=10)

    ax.set_title('Reflexion Execution Time Heatmap (seconds)', fontsize=13, fontweight='bold')

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Time (s)', rotation=-90, va='bottom')

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'fig12_time_heatmap.png', dpi=150, bbox_inches='tight')
    plt.savefig(FIGURES_PATH / 'fig12_time_heatmap.pdf', bbox_inches='tight')
    print("Saved: fig12_time_heatmap.png/pdf")

    # En uzun sureleri yazdir
    print("\n=== EN UZUN SURELI CASE'LER (Reflexion) ===")
    times_list = []
    for model in models:
        for case in cases:
            t = data.get((model, case, 'full_reflexion'), 0)
            times_list.append((model, case, t))

    times_list.sort(key=lambda x: x[2], reverse=True)

    print(f"{'Model':<12} {'Case':<8} {'Time (s)':<10}")
    print("-" * 30)
    for model, case, t in times_list[:10]:
        print(f"{model:<12} {case:<8} {t:.1f}")

if __name__ == "__main__":
    main()
