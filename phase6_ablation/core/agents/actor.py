# -*- coding: utf-8 -*-
"""
Actor Agent - Phase 6 (Optimized)
==================================

Phase-based Actor design:
- PHASE 1: DIAGNOSE - Gather information
- PHASE 2: FIX - Apply fix commands
- PHASE 3: STOP - No verify, no retry

Captures tool calls from message stream for trajectory logging.
"""

from claude_agent_sdk import query, ClaudeAgentOptions
from typing import Dict, Any, List, Optional


SYSTEM_PROMPT = """You are a Kubernetes troubleshooting expert.

Your task is to diagnose and fix a problematic Kubernetes pod.

## YOUR PROCESS (Follow these phases strictly):

### PHASE 1: DIAGNOSE
Run kubectl commands to understand the problem:
- kubectl get pod <name> -n <namespace>
- kubectl describe pod <name> -n <namespace>
- kubectl logs <name> -n <namespace> (if container started)
- kubectl get events -n <namespace>

### PHASE 2: FIX
Based on your diagnosis, apply the fix:
- Use kubectl patch, set image, apply, delete, etc.
- You may run multiple fix commands if needed

### PHASE 3: STOP
After applying the fix, output "FIX COMPLETE" and stop.
Do NOT verify the fix - an external Evaluator will check.
Do NOT retry if something fails - just report what you did.

## RULES:
- Execute commands via bash tool
- Be concise and efficient
- Do NOT run verification commands after fix
- Do NOT enter retry loops
- Always end with "FIX COMPLETE"

## CRITICAL - FORBIDDEN COMMANDS (will cause test failure):
- NEVER use 'kubectl edit' - it opens an interactive editor and BREAKS the test
- NEVER use vim, nano, vi, notepad, or any editor
- If you cannot patch a pod directly, DELETE it and RECREATE with correct spec
- Use 'kubectl delete pod X && kubectl apply -f' pattern instead of edit
"""


# R3.2 ablation variant: identical to SYSTEM_PROMPT except the verification
# ban in PHASE 3 / RULES is replaced by an explicit verify-and-retry allowance.
SYSTEM_PROMPT_SELF_VERIFY = """You are a Kubernetes troubleshooting expert.

Your task is to diagnose and fix a problematic Kubernetes pod.

## YOUR PROCESS (Follow these phases strictly):

### PHASE 1: DIAGNOSE
Run kubectl commands to understand the problem:
- kubectl get pod <name> -n <namespace>
- kubectl describe pod <name> -n <namespace>
- kubectl logs <name> -n <namespace> (if container started)
- kubectl get events -n <namespace>

### PHASE 2: FIX
Based on your diagnosis, apply the fix:
- Use kubectl patch, set image, apply, delete, etc.
- You may run multiple fix commands if needed

### PHASE 3: VERIFY
After applying the fix, verify that it worked:
- Re-check the pod status with kubectl get/describe
- If the problem persists, return to PHASE 1 and try a different fix
- You may repeat the diagnose-fix-verify cycle at most 3 times
When the pod is healthy, or you have used all cycles, output "FIX COMPLETE" and stop.

## RULES:
- Execute commands via bash tool
- Be concise and efficient
- Always end with "FIX COMPLETE"

## CRITICAL - FORBIDDEN COMMANDS (will cause test failure):
- NEVER use 'kubectl edit' - it opens an interactive editor and BREAKS the test
- NEVER use vim, nano, vi, notepad, or any editor
- If you cannot patch a pod directly, DELETE it and RECREATE with correct spec
- Use 'kubectl delete pod X && kubectl apply -f' pattern instead of edit
"""


class ActorAgent:
    """Actor agent for Kubernetes troubleshooting."""

    def __init__(self, model: str = "claude-haiku-4-5", verbose: bool = False,
                 self_verify: bool = False):
        self.model = model
        self.verbose = verbose
        self.self_verify = self_verify
        self.system_prompt = SYSTEM_PROMPT_SELF_VERIFY if self_verify else SYSTEM_PROMPT
        self.commands_executed = []  # Track all commands

    async def generate_trajectory(
        self,
        pod_name: str,
        namespace: str = "default",
        memory: Optional[List[str]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate a trajectory to fix the pod.

        Returns:
            Tuple of (trajectory_text, metadata)
            - trajectory includes all commands executed
        """
        print(f"\n[ACTOR] Generating trajectory for pod: {pod_name}")

        # Reset command tracking
        self.commands_executed = []
        pending_tool_calls = {}  # Track tool calls by ID

        prompt = self._build_prompt(pod_name, namespace, memory)

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            model=self.model,
            permission_mode="bypassPermissions"
        )

        trajectory = ""
        metadata = {}

        async for message in query(prompt=prompt, options=options):
            msg_type = type(message).__name__

            # Capture tool use from AssistantMessage
            if msg_type == 'AssistantMessage' and hasattr(message, 'content'):
                for block in message.content:
                    block_type = type(block).__name__

                    # Text block - add to trajectory
                    if block_type == 'TextBlock' and hasattr(block, 'text'):
                        trajectory += block.text

                    # ToolUseBlock - capture command
                    elif block_type == 'ToolUseBlock':
                        tool_name = getattr(block, 'name', '')
                        tool_input = getattr(block, 'input', {})
                        tool_id = getattr(block, 'id', '')

                        if tool_name == 'Bash':
                            command = tool_input.get('command', '')
                            if command:
                                pending_tool_calls[tool_id] = {
                                    'id': tool_id,
                                    'command': command,
                                    'output': None
                                }
                                print(f"  [BASH] $ {command[:100]}")

            # Capture tool result from UserMessage
            elif msg_type == 'UserMessage' and hasattr(message, 'content'):
                for block in message.content:
                    block_type = type(block).__name__

                    if block_type == 'ToolResultBlock':
                        tool_id = getattr(block, 'tool_use_id', '')
                        result = getattr(block, 'content', '')

                        if tool_id in pending_tool_calls:
                            pending_tool_calls[tool_id]['output'] = str(result)[:500]
                            self.commands_executed.append(pending_tool_calls[tool_id])
                            if self.verbose:
                                output_preview = str(result)[:100].replace('\n', ' ')
                                print(f"       -> {output_preview}")

            # Capture final metadata from ResultMessage
            elif msg_type == 'ResultMessage':
                metadata = {
                    'usage': getattr(message, 'usage', {}),
                    'cost_usd': getattr(message, 'total_cost_usd', None),
                    'duration_ms': getattr(message, 'duration_ms', 0),
                    'duration_api_ms': getattr(message, 'duration_api_ms', 0)
                }

        # Append command log to trajectory
        if self.commands_executed:
            trajectory += "\n\n## COMMANDS EXECUTED:\n"
            for i, cmd_info in enumerate(self.commands_executed, 1):
                trajectory += f"{i}. $ {cmd_info['command']}\n"
                if cmd_info.get('output'):
                    output_preview = cmd_info['output'][:200]
                    trajectory += f"   Output: {output_preview}...\n"

        # Add commands to metadata
        metadata['commands'] = self.commands_executed

        return trajectory.strip(), metadata

    def _build_prompt(
        self,
        pod_name: str,
        namespace: str,
        memory: Optional[List[str]]
    ) -> str:
        """Build the Actor prompt."""

        if self.self_verify:
            step3 = ('3. VERIFY: Check that the fix worked; if the problem persists, '
                     'diagnose and fix again (at most 3 cycles), then output "FIX COMPLETE"')
        else:
            step3 = '3. STOP: Output "FIX COMPLETE" (do not verify)'

        prompt = f"""## TASK
Fix the Kubernetes pod "{pod_name}" in namespace "{namespace}".

## STEPS
1. DIAGNOSE: Run kubectl get/describe/logs to find the problem
2. FIX: Apply kubectl commands to fix the issue
{step3}

"""

        # Add episodic memory if available
        if memory and len(memory) > 0:
            prompt += """## EPISODIC MEMORY (Learn from past failures)

"""
            for i, reflection in enumerate(memory):
                prompt += f"""### Trial {i + 1} Failed - Reflection:
{reflection}

"""
            prompt += """Use this memory to avoid repeating past mistakes.

"""

        prompt += """## OUTPUT
After fixing, briefly report:
1. What was wrong (diagnosis)
2. What you fixed (commands run)
3. End with "FIX COMPLETE"
"""

        return prompt
