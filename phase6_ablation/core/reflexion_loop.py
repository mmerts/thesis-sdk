# -*- coding: utf-8 -*-
"""
Reflexion Loop - Phase 6
=========================

Main orchestrator for the Reflexion pattern with ablation support.

Supports two configurations:
- baseline: max_trials=1, no reflection
- full_reflexion: max_trials=5, with reflection and memory
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .agents.actor import ActorAgent
from .agents.evaluator import ProgrammaticEvaluator
from .agents.self_reflection import SelfReflectionAgent
from .memory.episodic_memory import EpisodicMemory


@dataclass
class TrialResult:
    """Result of a single trial."""
    trial_num: int
    success: bool
    pod_status: str

    # Timing
    actor_time: float = 0.0
    eval_time: float = 0.0
    reflection_time: float = 0.0

    # Cost
    actor_cost: float = 0.0
    reflection_cost: float = 0.0

    # Tokens (detailed)
    actor_input_tokens: int = 0
    actor_output_tokens: int = 0
    actor_cache_read_tokens: int = 0
    actor_cache_creation_tokens: int = 0
    reflection_tokens: int = 0

    # Trajectory data
    trajectory: str = ""  # Full agent reasoning text
    commands: List[Dict[str, Any]] = field(default_factory=list)  # List of {command, output}

    # Reflection
    reflection_content: str = ""

    # Evaluation details
    eval_reason: str = ""


@dataclass
class ReflexionResult:
    """Result of the full Reflexion loop."""
    success: bool
    total_trials: int
    final_status: str
    trials: List[TrialResult] = field(default_factory=list)
    total_time: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0


class ReflexionLoop:
    """
    Reflexion loop orchestrator with ablation support.

    Parameters:
        max_trials: Maximum number of trials (1 for baseline, 5 for full)
        reflection_enabled: Whether to generate reflections on failure
        memory_size: Size of episodic memory (Ω parameter)
        model: Claude model to use
        verbose: Print detailed output
    """

    def __init__(
        self,
        max_trials: int = 5,
        reflection_enabled: bool = True,
        memory_size: int = 3,
        model: str = "claude-haiku-4-5-20251001",
        verbose: bool = False
    ):
        self.max_trials = max_trials
        self.reflection_enabled = reflection_enabled
        self.memory_size = memory_size
        self.model = model
        self.verbose = verbose

        # Initialize components
        self.actor = ActorAgent(model=model, verbose=True)  # Always verbose for debugging
        self.evaluator = ProgrammaticEvaluator(verbose=verbose)
        self.reflector = SelfReflectionAgent(model=model) if reflection_enabled else None
        self.memory = EpisodicMemory(max_size=memory_size)

    async def run(
        self,
        pod_name: str,
        namespace: str = "default",
        requires_connectivity_check: bool = False
    ) -> ReflexionResult:
        """
        Run the Reflexion loop.

        Args:
            pod_name: Name of the pod to fix
            namespace: Kubernetes namespace
            requires_connectivity_check: Whether to test actual service connectivity

        Returns:
            ReflexionResult with success status and metrics
        """
        self._requires_connectivity_check = requires_connectivity_check
        config_name = "full_reflexion" if self.reflection_enabled else "baseline"
        print(f"\n{'=' * 70}")
        print(f"REFLEXION LOOP [{config_name}]: {pod_name}")
        print(f"Max trials: {self.max_trials} | Reflection: {self.reflection_enabled}")
        print("=" * 70)

        result = ReflexionResult(
            success=False,
            total_trials=0,
            final_status="Unknown"
        )

        start_time = time.time()

        for trial_num in range(1, self.max_trials + 1):
            print(f"\n{'=' * 50}")
            print(f"TRIAL #{trial_num}/{self.max_trials}")
            print("=" * 50)

            trial_result = await self._run_trial(
                trial_num=trial_num,
                pod_name=pod_name,
                namespace=namespace
            )

            result.trials.append(trial_result)
            result.total_trials = trial_num

            if trial_result.success:
                result.success = True
                result.final_status = trial_result.pod_status
                print(f"\n[SUCCESS] Pod fixed in Trial #{trial_num}")
                break

            # Generate reflection if enabled and not last trial
            if self.reflection_enabled and self.reflector and trial_num < self.max_trials:
                reflection = await self._generate_reflection(
                    pod_name=pod_name,
                    trajectory=getattr(self, '_last_trajectory', ''),
                    evaluation={"pod_status": trial_result.pod_status}
                )
                if reflection:
                    self.memory.add(reflection)
                    trial_result.reflection_content = reflection

        if not result.success:
            result.final_status = result.trials[-1].pod_status if result.trials else "Unknown"
            print(f"\n[FAILED] Max trials ({self.max_trials}) reached")

        result.total_time = time.time() - start_time
        result.total_cost = sum(t.actor_cost + t.reflection_cost for t in result.trials)
        result.total_tokens = sum(
            t.actor_input_tokens + t.actor_output_tokens + t.reflection_tokens
            for t in result.trials
        )

        self._print_summary(result)

        return result

    async def _run_trial(
        self,
        trial_num: int,
        pod_name: str,
        namespace: str
    ) -> TrialResult:
        """Run a single trial."""

        trial = TrialResult(trial_num=trial_num, success=False, pod_status="Unknown")

        # Phase 1: Actor generates trajectory
        print(f"\n[TRIAL {trial_num}] ACTOR: Generating trajectory...")

        memory_to_use = self.memory.get_all() if self.reflection_enabled else None
        if memory_to_use:
            print(f"  [MEMORY] Using {len(memory_to_use)} reflection(s)")

        actor_start = time.time()
        trajectory, actor_meta = await self.actor.generate_trajectory(
            pod_name=pod_name,
            namespace=namespace,
            memory=memory_to_use
        )
        trial.actor_time = time.time() - actor_start

        self._last_trajectory = trajectory

        # Store trajectory and commands
        trial.trajectory = trajectory
        trial.commands = actor_meta.get('commands', []) if actor_meta else []

        if actor_meta:
            trial.actor_cost = actor_meta.get('cost_usd', 0) or 0
            usage = actor_meta.get('usage', {})
            if usage:
                trial.actor_input_tokens = usage.get('input_tokens', 0)
                trial.actor_output_tokens = usage.get('output_tokens', 0)
                trial.actor_cache_read_tokens = usage.get('cache_read_input_tokens', 0)
                trial.actor_cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)

        print(f"  [TRAJECTORY] {len(trajectory)} chars, {len(trial.commands)} commands")
        print(f"  [TIMING] Actor: {trial.actor_time:.1f}s")

        # Phase 2: Evaluator checks result
        print(f"\n[TRIAL {trial_num}] EVALUATOR: Checking pod status...")

        eval_start = time.time()
        evaluation, eval_meta = await self.evaluator.evaluate(
            pod_name=pod_name,
            namespace=namespace,
            wait_time=5,
            requires_connectivity_check=getattr(self, '_requires_connectivity_check', False)
        )
        trial.eval_time = time.time() - eval_start

        trial.success = evaluation.get('success', False)
        trial.pod_status = evaluation.get('pod_status', 'Unknown')
        trial.eval_reason = evaluation.get('reason', 'Unknown')

        status_icon = "[+]" if trial.success else "[-]"
        print(f"\n{status_icon} EVALUATION: {'SUCCESS' if trial.success else 'FAILURE'}")
        print(f"   Reason: {trial.eval_reason}")
        print(f"   Pod Status: {trial.pod_status}")
        print(f"  [TIMING] Evaluator: {trial.eval_time:.1f}s")

        return trial

    async def _generate_reflection(
        self,
        pod_name: str,
        trajectory: str,
        evaluation: Dict[str, Any]
    ) -> Optional[str]:
        """Generate reflection on failure."""

        if not self.reflector:
            return None

        print(f"\n[REFLECTION] Generating...")

        refl_start = time.time()
        reflection, refl_meta = await self.reflector.reflect(
            pod_name=pod_name,
            trajectory=trajectory,
            evaluation=evaluation,
            memory=self.memory.get_all()
        )
        refl_time = time.time() - refl_start

        print(f"  [TIMING] Reflection: {refl_time:.1f}s")

        return reflection

    def _print_summary(self, result: ReflexionResult) -> None:
        """Print final summary."""
        print(f"\n{'=' * 70}")
        print("REFLEXION LOOP SUMMARY")
        print("=" * 70)
        print(f"Total Trials: {result.total_trials}/{self.max_trials}")
        print(f"Final Status: {'[+] SUCCESS' if result.success else '[-] FAILED'}")
        print(f"Pod Status: {result.final_status}")
        print(f"Total Time: {result.total_time:.1f}s")
        print(f"Total Cost: ${result.total_cost:.4f}")
        print("=" * 70)
