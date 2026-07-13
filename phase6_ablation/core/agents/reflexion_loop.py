# -*- coding: utf-8 -*-
"""
Reflexion Loop Orchestrator - Phase 5 Optimized
=================================================

Implements Algorithm 1 from the Reflexion paper with optimizations:
- Actor: Claude Agent SDK (agentic - needs tool use)
- Evaluator: Programmatic Python (NO LLM - fast & cheap)
- Self-Reflection: Single LLM call (NO agentic loop)

From paper (Section 3):
"Reflexion augments agents with dynamic memory and self-reflection capabilities
 to enhance their existing reasoning abilities."

Phase 5 Architecture:
┌─────────────────────────────────────────────────────────────┐
│  Trial Loop                                                  │
├─────────────────────────────────────────────────────────────┤
│  1. Actor (Claude Agent SDK)  ─────> trajectory             │
│     - Runs kubectl via bash tool                            │
│     - Agentic loop with tool calls                          │
│                                                             │
│  2. Evaluator (Python)        ─────> success/fail           │
│     - kubectl get pod -o json                               │
│     - NO LLM calls (fast!)                                  │
│                                                             │
│  3. Self-Reflection (Single LLM call)  ─────> reflection    │
│     - Only on failure                                       │
│     - Direct API call, no tools                             │
└─────────────────────────────────────────────────────────────┘
"""

from typing import Dict, Any, List
from .actor import ActorAgent
from .programmatic_evaluator import ProgrammaticEvaluator
from .self_reflection import SelfReflectionAgent
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from memory.episodic_memory import EpisodicMemory


class ReflexionLoop:
    """
    Optimized Reflexion pattern loop.

    Key differences from Phase 4:
    - Programmatic evaluator (no LLM)
    - Single-call reflection (no agentic loop)
    - Only Actor uses Agent SDK
    """

    def __init__(
        self,
        max_trials: int = 5,
        memory_size: int = 3,
        model: str = "claude-haiku-4-5",
        verbose: bool = False,
        reflection_enabled: bool = True
    ):
        """
        Initialize Reflexion Loop.

        Args:
            max_trials: Maximum trials before giving up
            memory_size: Max reflections to store (Omega parameter)
            model: Claude model for Actor and Self-Reflection
            verbose: If True, print detailed logs
            reflection_enabled: If False, skip reflection generation (for ablation study)
        """
        self.max_trials = max_trials
        self.verbose = verbose
        self.reflection_enabled = reflection_enabled

        # Initialize agents
        self.actor = ActorAgent(model=model, verbose=verbose)
        self.evaluator = ProgrammaticEvaluator(verbose=verbose)
        self.reflector = SelfReflectionAgent(model=self._get_reflection_model(model))

        # Initialize episodic memory
        self.memory = EpisodicMemory(max_size=memory_size)

    def _get_reflection_model(self, model: str) -> str:
        """Convert model name to full model ID for direct API calls."""
        model_mapping = {
            "claude-haiku-4-5": "claude-haiku-4-5-20251001",
            "claude-3-5-haiku": "claude-3-5-haiku-20241022",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-sonnet-4-5": "claude-sonnet-4-5-20250514",
            "claude-sonnet-4": "claude-sonnet-4-20250514"
        }
        return model_mapping.get(model, model)

    async def run(
        self,
        pod_name: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Run the Reflexion loop for pod troubleshooting.

        Args:
            pod_name: Name of the problematic pod
            namespace: Kubernetes namespace

        Returns:
            Dict with results and metrics
        """
        print("\n" + "=" * 80)
        print(f"REFLEXION LOOP (Phase 5 Optimized): {pod_name}")
        print(f"Max trials: {self.max_trials} | Memory size: {self.memory.max_size}")
        print("=" * 80)

        # Track results
        trajectories = []
        evaluations = []
        reflections = []
        timings = []
        api_metadata = []

        # Clear memory (fresh start)
        self.memory.clear()

        # Trial loop (Algorithm 1)
        trial = 0
        success = False

        while trial < self.max_trials:
            print(f"\n{'=' * 80}")
            print(f"TRIAL #{trial + 1}/{self.max_trials}")
            print("=" * 80)

            # Step 1: Actor generates trajectory
            print(f"\n[TRIAL {trial + 1}] ACTOR: Generating trajectory...")

            memory_list = self.memory.get_all() if not self.memory.is_empty() else None

            if memory_list:
                print(f"  [MEMORY] Using {len(memory_list)} reflection(s)")

            actor_start = time.time()
            trajectory, actor_metadata = await self.actor.generate_trajectory(
                pod_name=pod_name,
                namespace=namespace,
                memory=memory_list
            )
            actor_duration = time.time() - actor_start

            trajectories.append(trajectory)
            print(f"\n  [TRAJECTORY] Length: {len(trajectory)} chars")
            print(f"  [TIMING] Actor: {actor_duration:.2f}s")

            # Step 2: Evaluator checks if successful (PROGRAMMATIC - NO LLM!)
            print(f"\n[TRIAL {trial + 1}] EVALUATOR: Checking pod status...")

            evaluator_start = time.time()
            evaluation, evaluator_metadata = await self.evaluator.evaluate(
                pod_name=pod_name,
                namespace=namespace,
                wait_time=5
            )
            evaluator_duration = time.time() - evaluator_start

            evaluations.append(evaluation)

            # Display evaluation result
            print(self.evaluator.format_result(evaluation))
            print(f"  [TIMING] Evaluator: {evaluator_duration:.2f}s (NO LLM)")

            # Step 3: Check if success (early stopping)
            if evaluation.get("success", False):
                print(f"\n[SUCCESS] Pod fixed in Trial #{trial + 1}")

                timings.append({
                    "actor": actor_duration,
                    "evaluator": evaluator_duration,
                    "reflection": 0,
                    "total": actor_duration + evaluator_duration
                })

                api_metadata.append({
                    "actor": actor_metadata,
                    "evaluator": evaluator_metadata,
                    "reflection": {}
                })

                success = True
                break

            # Step 4: Generate self-reflection (SINGLE LLM CALL - NO AGENTIC LOOP!)
            if self.reflection_enabled:
                print(f"\n[TRIAL {trial + 1}] REFLECTION: Analyzing failure...")

                reflection_start = time.time()
                reflection, reflection_metadata = await self.reflector.reflect(
                    pod_name=pod_name,
                    trajectory=trajectory,
                    evaluation=evaluation,
                    memory=self.memory.get_all()
                )
                reflection_duration = time.time() - reflection_start

                reflections.append(reflection)
                print(f"  [TIMING] Reflection: {reflection_duration:.2f}s (single call)")

                # Store timing for failed trial
                timings.append({
                    "actor": actor_duration,
                    "evaluator": evaluator_duration,
                    "reflection": reflection_duration,
                    "total": actor_duration + evaluator_duration + reflection_duration
                })

                api_metadata.append({
                    "actor": actor_metadata,
                    "evaluator": evaluator_metadata,
                    "reflection": reflection_metadata
                })

                # Step 5: Add reflection to memory
                self.memory.add(reflection)
                print(f"\n[MEMORY] Reflection added for Trial #{trial + 2}")
            else:
                # Reflection disabled - skip reflection generation
                print(f"\n[TRIAL {trial + 1}] REFLECTION: Disabled (ablation study mode)")

                timings.append({
                    "actor": actor_duration,
                    "evaluator": evaluator_duration,
                    "reflection": 0,
                    "total": actor_duration + evaluator_duration
                })

                api_metadata.append({
                    "actor": actor_metadata,
                    "evaluator": evaluator_metadata,
                    "reflection": {}
                })

            trial += 1

        # Final summary
        if not success:
            print(f"\n[FAILED] Max trials ({self.max_trials}) reached")

        return {
            "success": success,
            "total_trials": trial + 1,
            "final_status": evaluations[-1].get("pod_status", "Unknown") if evaluations else "Unknown",
            "trajectories": trajectories,
            "reflections": reflections,
            "evaluations": evaluations,
            "timings": timings,
            "api_metadata": api_metadata
        }

    def format_summary(self, result: Dict[str, Any]) -> str:
        """Format execution summary for display."""
        summary = "\n" + "=" * 80 + "\n"
        summary += "REFLEXION LOOP SUMMARY (Phase 5 Optimized)\n"
        summary += "=" * 80 + "\n"

        summary += f"Total Trials: {result['total_trials']}/{self.max_trials}\n"
        summary += f"Final Status: {'[+] SUCCESS' if result['success'] else '[-] FAILED'}\n"
        summary += f"Pod Status: {result['final_status']}\n"
        summary += f"Reflections Generated: {len(result['reflections'])}\n"

        # Calculate total time
        total_time = sum(t.get('total', 0) for t in result.get('timings', []))
        summary += f"Total Time: {total_time:.2f}s\n"

        summary += "\nTrial Breakdown:\n"
        summary += "-" * 80 + "\n"

        for i in range(result['total_trials']):
            summary += f"  Trial #{i + 1}:\n"

            if i < len(result['evaluations']):
                eval_result = result['evaluations'][i]
                status_str = "[+] Success" if eval_result.get('success') else "[-] Failed"
                summary += f"    Status: {status_str}\n"
                summary += f"    Pod Status: {eval_result.get('pod_status', 'Unknown')}\n"

            if i < len(result['timings']):
                timing = result['timings'][i]
                summary += f"    Timing: Actor={timing.get('actor', 0):.1f}s, "
                summary += f"Eval={timing.get('evaluator', 0):.1f}s, "
                summary += f"Refl={timing.get('reflection', 0):.1f}s\n"

            summary += "\n"

        summary += "=" * 80 + "\n"

        return summary
