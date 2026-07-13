# -*- coding: utf-8 -*-
"""
Actor Agent with Thinking Capture
==================================

Extended version that captures agent's "thinking" process.
Used for contamination test to understand WHY agent makes decisions.

Captures:
- TextBlock: Regular text output
- ToolUseBlock: Commands executed
- ToolResultBlock: Command outputs
- ThinkingBlock: Agent's internal reasoning (if available)
"""

from claude_agent_sdk import query, ClaudeAgentOptions
from typing import Dict, Any, List, Optional
from datetime import datetime


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


class ActorAgentWithThinking:
    """Actor agent with full thinking/reasoning capture."""

    def __init__(self, model: str = "claude-haiku-4-5", verbose: bool = True):
        self.model = model
        self.verbose = verbose
        self.commands_executed = []
        self.thinking_log = []  # NEW: Capture all thinking blocks
        self.message_log = []   # NEW: Full message log for analysis

    async def generate_trajectory(
        self,
        pod_name: str,
        namespace: str = "default",
        memory: Optional[List[str]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate a trajectory to fix the pod.

        Enhanced to capture thinking/reasoning blocks.
        """
        print(f"\n[ACTOR] Generating trajectory for pod: {pod_name}")
        print(f"[ACTOR] Model: {self.model}")
        print(f"[ACTOR] Thinking capture: ENABLED")

        # Reset tracking
        self.commands_executed = []
        self.thinking_log = []
        self.message_log = []
        pending_tool_calls = {}

        prompt = self._build_prompt(pod_name, namespace, memory)

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=self.model,
            permission_mode="bypassPermissions"
        )

        trajectory = ""
        metadata = {}
        step_count = 0

        async for message in query(prompt=prompt, options=options):
            msg_type = type(message).__name__
            timestamp = datetime.now().isoformat()
            step_count += 1

            # Log every message for analysis
            message_entry = {
                "step": step_count,
                "timestamp": timestamp,
                "type": msg_type,
                "content_types": []
            }

            # Process AssistantMessage
            if msg_type == 'AssistantMessage' and hasattr(message, 'content'):
                for block in message.content:
                    block_type = type(block).__name__
                    message_entry["content_types"].append(block_type)

                    # Text block - add to trajectory
                    if block_type == 'TextBlock' and hasattr(block, 'text'):
                        text = block.text
                        trajectory += text

                        if self.verbose and text.strip():
                            preview = text[:100].replace('\n', ' ')
                            print(f"  [TEXT] {preview}...")

                    # Thinking block - CAPTURE reasoning
                    elif block_type == 'ThinkingBlock' and hasattr(block, 'thinking'):
                        thinking = block.thinking
                        self.thinking_log.append({
                            "step": step_count,
                            "timestamp": timestamp,
                            "thinking": thinking
                        })

                        if self.verbose:
                            preview = thinking[:150].replace('\n', ' ')
                            print(f"  [THINKING] {preview}...")

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
                                    'step': step_count,
                                    'timestamp': timestamp,
                                    'command': command,
                                    'output': None,
                                    # Link to preceding thinking
                                    'preceding_thinking': self.thinking_log[-1] if self.thinking_log else None
                                }
                                print(f"  [BASH] $ {command[:100]}")

            # Capture tool result from UserMessage
            elif msg_type == 'UserMessage' and hasattr(message, 'content'):
                for block in message.content:
                    block_type = type(block).__name__
                    message_entry["content_types"].append(block_type)

                    if block_type == 'ToolResultBlock':
                        tool_id = getattr(block, 'tool_use_id', '')
                        result = getattr(block, 'content', '')

                        if tool_id in pending_tool_calls:
                            pending_tool_calls[tool_id]['output'] = str(result)[:1000]
                            self.commands_executed.append(pending_tool_calls[tool_id])

                            if self.verbose:
                                output_preview = str(result)[:80].replace('\n', ' ')
                                print(f"       -> {output_preview}")

            # Capture final metadata from ResultMessage
            elif msg_type == 'ResultMessage':
                metadata = {
                    'usage': {},
                    'cost_usd': getattr(message, 'total_cost_usd', None),
                    'duration_ms': getattr(message, 'duration_ms', 0),
                    'duration_api_ms': getattr(message, 'duration_api_ms', 0)
                }

                # Try to get usage details
                if hasattr(message, 'usage'):
                    usage = message.usage
                    if hasattr(usage, '__dict__'):
                        metadata['usage'] = usage.__dict__
                    elif isinstance(usage, dict):
                        metadata['usage'] = usage

            self.message_log.append(message_entry)

        # Build enhanced trajectory with command log
        if self.commands_executed:
            trajectory += "\n\n## COMMANDS EXECUTED:\n"
            for i, cmd_info in enumerate(self.commands_executed, 1):
                trajectory += f"{i}. $ {cmd_info['command']}\n"
                if cmd_info.get('output'):
                    output_preview = cmd_info['output'][:200]
                    trajectory += f"   Output: {output_preview}...\n"

        # Add enhanced metadata
        metadata['commands'] = self.commands_executed
        metadata['thinking_log'] = self.thinking_log
        metadata['message_log'] = self.message_log
        metadata['total_steps'] = step_count
        metadata['total_thinking_blocks'] = len(self.thinking_log)

        # Print summary
        print(f"\n[ACTOR] Completed:")
        print(f"  - Total steps: {step_count}")
        print(f"  - Commands executed: {len(self.commands_executed)}")
        print(f"  - Thinking blocks captured: {len(self.thinking_log)}")

        return trajectory.strip(), metadata

    def _build_prompt(
        self,
        pod_name: str,
        namespace: str,
        memory: Optional[List[str]]
    ) -> str:
        """Build the Actor prompt."""

        prompt = f"""## TASK
Fix the Kubernetes pod "{pod_name}" in namespace "{namespace}".

## STEPS
1. DIAGNOSE: Run kubectl get/describe/logs to find the problem
2. FIX: Apply kubectl commands to fix the issue
3. STOP: Output "FIX COMPLETE" (do not verify)

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

    def get_thinking_summary(self) -> str:
        """Get a summary of all captured thinking."""
        if not self.thinking_log:
            return "No thinking blocks captured."

        summary = f"Total thinking blocks: {len(self.thinking_log)}\n\n"
        for i, entry in enumerate(self.thinking_log, 1):
            summary += f"--- Thinking Block {i} (Step {entry['step']}) ---\n"
            summary += entry['thinking'][:500]
            if len(entry['thinking']) > 500:
                summary += "...[truncated]"
            summary += "\n\n"

        return summary
