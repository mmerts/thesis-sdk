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

Four post-hoc controls were added during peer review and run on the three models still available through the API (Haiku 4.5, Sonnet 4.5, Opus 4.5): **feedback-only** (`two_try_feedback`: the retry receives the evaluator's verbatim failure reason, no reflection), **reflection with reason** (`full_reflexion_feedback`: as Reflexion, but the reflection prompt also receives the evaluator's failure reason), **self-verify** (`baseline_self_verify`: one attempt in which the actor may verify and revise its own fix), and **stabilization window** (`baseline_settle`: the single-attempt baseline, evaluated with a bounded 90 s stabilization window; the first sample reproduces the original five-second protocol and is recorded separately as `eval_first_success` in each run's JSON).

## Repository Structure

```
phase6_ablation/
├── core/                 # Reflexion loop: actor, evaluator, self-reflection, episodic memory
│   ├── agents/           #   actor.py, evaluator.py (programmatic, LLM-free), self_reflection.py
│   ├── memory/           #   episodic_memory.py (FIFO, Ω = 3)
│   ├── configs/          #   experiment_configs.py (baseline / two-try / Reflexion + post-hoc controls)
│   └── reflexion_loop.py #   trial loop used for all reported runs
├── runners/              # experiment_runner.py: runner used for all reported runs
├── prompts/              # Actor and self-reflection prompt templates
├── tools/                # run_test.py (single run), ablation_test_runner.py (batch)
├── scripts/              # create_database.py, analysis scripts, post-hoc control runners (run_*_experiment.py)
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
| `config` | `baseline`, `two_try_no_reflection` ("two-try"), `full_reflexion` ("Reflexion"); post-hoc controls: `two_try_feedback`, `full_reflexion_feedback`, `baseline_self_verify`, `baseline_settle` |
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

**Note on run counts:** the database contains 2,334 runs in total. The paper's main analysis uses the original experiment matrix of 1,500 runs (cases 1–10, 10 runs per cell). A further 310 runs of the three main configurations were collected after that analysis was frozen: extended repetitions of the two multi-fault scenarios (`case9`, `case10`) and an exploratory two-fault scenario (`case11`, ConfigMap + selector). The remaining 524 runs are the post-hoc controls: `two_try_feedback` (142), `full_reflexion_feedback` (142), `baseline_self_verify` (120) and `baseline_settle` (120). The controls on `case9`/`case10` use the current instantiation of those scenarios, in which the agent is pointed at the faulty deployment; they are compared only with post-freeze runs (`run_id > 10`) of the other configurations, not with the matrix runs. Raw per-run JSON logs, including full command trajectories, are under `phase6_ablation/results/raw/`. A few run identifiers were executed more than once and therefore have several JSON files; `results.db` keeps the last execution. One of them lies inside the 1,500-run matrix: `haiku30_baseline_case6_run1` failed in the matrix run (2025-12-02) and succeeded when re-executed on 2026-01-07. The paper reports the matrix run (baseline 193/500), so a plain query of `results.db` returns 194/500 for the baseline.

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

Run the post-hoc controls (resumable; `--dry-run` and `--pilot` are supported):

```bash
python phase6_ablation/scripts/run_feedback_experiment.py             # two_try_feedback
python phase6_ablation/scripts/run_reflection_feedback_experiment.py  # full_reflexion_feedback
python phase6_ablation/scripts/run_self_verify_experiment.py          # baseline_self_verify
python phase6_ablation/scripts/run_settle_experiment.py               # baseline_settle
```

**Which loop produced the reported runs:** every run in `results.db` was produced by `phase6_ablation/runners/experiment_runner.py`, which drives `phase6_ablation/core/reflexion_loop.py`. In that loop the self-reflection call receives the failed trajectory, the pod status and prior reflections, but **not** the evaluator's textual failure reason (the reason field of the reflection prompt is left at its default); only the `full_reflexion_feedback` control fills it. The convenience tools `tools/run_test.py` and `tools/ablation_test_runner.py` import an older loop variant, `phase6_ablation/core/agents/reflexion_loop.py`, which does pass the evaluator's reason to the reflection call and does not implement the post-hoc controls. That variant was not used for any reported run; use the runner above to reproduce the paper's conditions.

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
