# -*- coding: utf-8 -*-
"""
Self-Reflection Agent (Msr) - Phase 5 Optimized Component
==========================================================

SINGLE LLM CALL - No agentic tool loops, just direct text generation.

From Reflexion paper (Section 3.2):
"Msr generates verbal self-reflections to provide the agent with nuanced and
 specific feedback on its performance decisions."

This implementation uses a single LLM call with Anthropic's Messages API
instead of the Agent SDK's agentic loop. This is more efficient because
reflection doesn't need tool use - it just needs to analyze text.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

import anthropic
from typing import Dict, Any, List, Optional, Tuple
import time


class SelfReflectionAgent:
    """
    Self-Reflection agent using direct API calls.

    SINGLE LLM CALL - no tools, no agentic loop.

    This aligns with Reflexion paper where reflection is a
    text generation task conditioned on trajectory + evaluation.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        """
        Initialize Self-Reflection agent.

        Args:
            model: Claude model to use (default: Haiku for cost efficiency)
        """
        self.model = model
        self.client = anthropic.Anthropic()

    async def reflect(
        self,
        pod_name: str,
        trajectory: str,
        evaluation: Dict[str, Any],
        memory: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate self-reflection from a failed attempt.

        SINGLE API CALL - no tool use, just text generation.

        Args:
            pod_name: Name of the pod being fixed
            trajectory: The Actor's trajectory (actions taken)
            evaluation: The Evaluator's result (failure details)
            memory: Previous reflections (for context)

        Returns:
            Tuple of (reflection, metadata):
            - reflection: Self-reflection as natural language text
            - metadata: Dict with usage, cost, timing
        """
        print(f"\n[SELF-REFLECTION] Analyzing failure for pod: {pod_name}")

        prompt = self._build_reflection_prompt(
            pod_name,
            trajectory,
            evaluation,
            memory
        )

        system_prompt = self._get_system_prompt()

        # Make single API call
        start_time = time.time()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        duration_ms = (time.time() - start_time) * 1000

        # Extract reflection text
        reflection = ""
        for block in response.content:
            if hasattr(block, 'text'):
                reflection += block.text

        # Build metadata
        metadata = {
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            "cost_usd": self._calculate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens
            ),
            "duration_ms": duration_ms,
            "duration_api_ms": duration_ms,
            "reflection_type": "single_call"
        }

        print(f"  [REFLECTION] Generated ({len(reflection)} chars)")
        print(f"  [TOKENS] Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")

        return reflection.strip(), metadata

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost based on model pricing.

        Haiku 4.5 pricing (as of 2024):
        - Input: $1.00 / 1M tokens
        - Output: $5.00 / 1M tokens
        """
        # Haiku 4.5 pricing
        input_cost_per_million = 1.0
        output_cost_per_million = 5.0

        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million

        return input_cost + output_cost

    def _build_reflection_prompt(
        self,
        pod_name: str,
        trajectory: str,
        evaluation: Dict[str, Any],
        memory: Optional[List[str]]
    ) -> str:
        """Build the Self-Reflection prompt."""
        prompt = f"""You are analyzing a FAILED attempt to fix Kubernetes pod "{pod_name}".

**YOUR TASK:** Generate a self-reflection explaining what went wrong and how to improve.

**TRAJECTORY (What was attempted):**
{trajectory}

**EVALUATION RESULT (Why it failed):**
- Success: {evaluation.get('success', False)}
- Reason: {evaluation.get('reason', 'Unknown')}
- Pod Status: {evaluation.get('pod_status', 'Unknown')}
- Ready: {evaluation.get('pod_ready', 'N/A')}

"""

        # Add context from previous reflections
        if memory and len(memory) > 0:
            prompt += """**PREVIOUS REFLECTIONS (What we learned before):**
"""
            for i, prev_reflection in enumerate(memory, 1):
                prompt += f"""
Attempt #{i} Reflection:
{prev_reflection}

"""

        prompt += """**YOUR REFLECTION MUST:**

1. **CREDIT ASSIGNMENT:** Identify WHICH specific action or decision caused the failure
   - Don't just say "it failed" - explain WHY it failed
   - Which kubectl command was incorrect?
   - Was the diagnosis wrong?
   - Was the fix incomplete?

2. **ROOT CAUSE:** Explain the actual underlying problem
   - What did I misunderstand about the pod's state?
   - What information did I miss or misinterpret?

3. **CONCRETE NEXT STEPS:** Suggest specific actions for the next attempt
   - What should I check or verify next time?
   - What different approach should I try?
   - What command or fix should I use instead?

**FORMAT:** Write in FIRST PERSON (use "I" statements).
Be specific and actionable, not vague. Keep it concise (200-400 words).

Generate your self-reflection now:
"""

        return prompt

    def _get_system_prompt(self) -> str:
        """Get the Self-Reflection agent's system prompt."""
        return """You are a Self-Reflection agent (Msr) in the Reflexion framework.

Your role:
- Analyze FAILED troubleshooting attempts
- Perform credit assignment: identify the specific action that caused failure
- Generate first-person verbal reflections
- Provide concrete, actionable suggestions for improvement

Your reflections are stored in episodic memory and used by the Actor in future trials.

Be:
- Specific (not vague)
- Actionable (concrete next steps)
- Analytical (explain WHY it failed)
- First-person ("I failed because...")
- Concise (200-400 words)

This is verbal reinforcement learning - your reflection guides the Actor to improve."""
