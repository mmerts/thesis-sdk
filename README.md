# Reflexion-K8s: Replication Package

Experiment harness, benchmark scenarios, and results dataset for the paper:

> **AI-Driven Kubernetes Incident Remediation with the Reflexion Framework**
> Mustafa Mert Suerkan, Emin Kugu, Hakan Emekci
> Department of Computer Engineering, TED University, Ankara, Turkey

## Overview

This repository contains an autonomous LLM agent system that diagnoses and fixes Kubernetes misconfigurations using the **Reflexion** framework (Shinn et al., NeurIPS 2023). After a failed attempt, a self-reflection module generates a verbal analysis of the failure (credit assignment, root cause, next steps), which is stored in a bounded episodic memory and injected into the agent's prompt on the next attempt.

```
Actor ──► Evaluator ──► success? ──► End
                │ fail
                ▼
        Self-Reflection ──► Episodic Memory ──► Retry (fresh context + reflections)
```

The paper evaluates three configurations — **baseline** (single attempt), **two-try** (retry without reflection, an ablation control), and **Reflexion** (retry guided by reflection) — across 5 Claude models on 8 single-fault scenarios from KubeLLMBench plus 2 multi-fault scenarios: 5 models × 10 scenarios × 3 configurations × 10 runs = 1,500 analyzed experiments.

## Repository Structure

```
phase6_ablation/
├── core/                 # Reflexion loop: actor, evaluator, self-reflection, episodic memory
│   ├── agents/           #   actor.py, evaluator.py (programmatic, LLM-free), self_reflection.py
│   ├── memory/           #   episodic_memory.py (FIFO, Ω = 3)
│   └── configs/          #   experiment_configs.py (baseline / two-try / Reflexion)
├── prompts/              # Actor and self-reflection prompt templates
├── tools/                # run_test.py (single run), ablation_test_runner.py (batch)
├── scripts/              # create_database.py and analysis scripts
├── figures/              # Result figures (PDF/PNG)
└── results/
    ├── raw/              # Per-run JSON logs (full command trajectory, tokens, cost, verdict)
    └── results.db        # SQLite database aggregating all runs

kubernetes-troubleshooting-cases/   # Benchmark scenarios (setup.sh, clean.sh, manifests)
requirements.txt
```

## Benchmark Scenarios

Cases 1–8 are the single-fault scenarios defined in KubeLLMBench (De Jesus et al., IEEE Cloud Summit 2025); cases 9–10 are multi-fault scenarios of our own design. Each scenario lives in `kubernetes-troubleshooting-cases/{N}_{name}/` with a `setup.sh` that deploys the intentionally misconfigured manifests into a dedicated namespace and a `clean.sh` that tears it down.

| # | Name | Fault(s) |
|---|------|----------|
| 1 | Wrong Port | Container port mismatch |
| 2 | Incorrect Selector | Service selector does not match pod labels |
| 3 | Liveness Probe | Probe misconfiguration causes restarts |
| 4 | Wrong Interface | App binds to localhost only |
| 5 | Port Mismatch | Multi-port service/container conflict |
| 6 | Image Typo | Misspelled image name (ImagePullBackOff) |
| 7 | Volume Mount | ConfigMap reference error |
| 8 | Env Variable | Missing required environment variable |
| 9 | Double Trouble | Image typo + wrong service port (2 faults) |
| 10 | Triple Threat | Image + port + selector (3 faults) |

## Dataset

The full per-run log is in **`phase6_ablation/results/results.db`** (SQLite). The main table is `experiments`:

| Column | Description |
|--------|-------------|
| `model` | `haiku30`, `haiku35`, `haiku45`, `sonnet45`, `opus45` |
| `config` | `baseline`, `two_try_no_reflection` ("two-try"), `full_reflexion` ("Reflexion") |
| `case_id` | `case1` … `case11` |
| `success` | Binary outcome from the programmatic evaluator |
| `trials_used`, `total_time`, `total_cost`, `total_tokens` | Per-run measurements |

Example — reproduce the paper's Table 2 (success rate by model and configuration):

```sql
SELECT model, config, ROUND(100.0 * AVG(success), 1) AS success_pct
FROM experiments
WHERE case_id IN ('case1','case2','case3','case4','case5','case6','case7','case8')
GROUP BY model, config;
```

**Note on run counts:** the database contains 1,810 runs in total. The paper analyzes the original experiment matrix of 1,500 runs (cases 1–10, 10 runs per cell). The additional runs were collected after the paper's analysis was frozen: extended repetitions of the two multi-fault scenarios (`case9`, `case10`) and an exploratory two-fault scenario (`case11`, ConfigMap + selector) that is not analyzed in the paper. Raw per-run JSON logs, including full command trajectories, are under `phase6_ablation/results/raw/`.

## Reproducing the Experiments

**Prerequisites:** Docker Desktop, Minikube (v1.32 used in the paper), Python 3.11, and an Anthropic API key.

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
minikube start
```

Run a single experiment:

```bash
python phase6_ablation/tools/run_test.py --model haiku45 --case case1 --config full_reflexion
```

Run the batch experiment matrix:

```bash
python phase6_ablation/tools/ablation_test_runner.py
```

Rebuild the SQLite database from the raw JSON logs:

```bash
python phase6_ablation/scripts/create_database.py
```

Note that LLM outputs are non-deterministic and API costs apply; the paper mitigates this with 10–25 repeated runs per (model, scenario, configuration) cell. All statistics reported in the paper are computed directly from `results.db`.

## Key Results

| Configuration | Success rate (all 10 scenarios) |
|---------------|--------------------------------|
| Baseline (1 attempt) | 38.6% |
| Two-try (retry, no reflection) | 68.4% |
| Reflexion (retry + reflection) | 69.2% |

The second attempt itself drives nearly all of the improvement: the retry effect is statistically significant, while the overall difference between plain retry and reflection-guided retry is not. On the **multi-fault** scenarios, reflection shows a positive trend over plain retry (≈ +12 pp), which the paper treats as a preliminary, hypothesis-generating result. Haiku 4.5 is the most cost-efficient model at ≈ $0.14 per successful resolution.

## Citation

If you use this code or dataset, please cite:

```
M. M. Suerkan, E. Kugu, and H. Emekci, "AI-Driven Kubernetes Incident
Remediation with the Reflexion Framework," 2026. (under review)
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE).
