# -*- coding: utf-8 -*-
"""
Episodic Memory for Reflexion
==============================

Stores self-reflections from past trials as text.
Implements bounded memory (Omega parameter from paper).

From Reflexion paper:
- Memory stores verbal reflections from failed attempts
- Bounded to last Omega reflections (typically 1-3)
- Acts as "long-term memory" for the Actor
"""

from typing import List, Optional


class EpisodicMemory:
    """
    Episodic memory for storing self-reflections.

    Implements bounded FIFO queue:
    - Stores last Omega reflections
    - Older reflections are discarded when limit reached
    - All reflections are natural language text
    """

    def __init__(self, max_size: int = 3):
        """
        Initialize episodic memory.

        Args:
            max_size: Maximum number of reflections to store (Omega parameter)
        """
        self.max_size = max_size
        self.reflections: List[str] = []

    def add(self, reflection: str) -> None:
        """
        Add a new reflection to memory.

        If memory is full, oldest reflection is removed (FIFO).
        """
        if not reflection or not reflection.strip():
            return

        self.reflections.append(reflection.strip())

        # Enforce bounded memory
        if len(self.reflections) > self.max_size:
            self.reflections.pop(0)

    def get_all(self) -> List[str]:
        """Get all stored reflections."""
        return self.reflections.copy()

    def get_latest(self) -> Optional[str]:
        """Get the most recent reflection."""
        return self.reflections[-1] if self.reflections else None

    def get_formatted(self) -> str:
        """Get all reflections formatted as a single text block."""
        if not self.reflections:
            return "No previous reflections."

        formatted = "Previous learnings from failed attempts:\n\n"
        for i, reflection in enumerate(self.reflections, 1):
            formatted += f"{i}. {reflection}\n\n"

        return formatted.strip()

    def clear(self) -> None:
        """Clear all reflections from memory."""
        self.reflections = []

    def size(self) -> int:
        """Get current number of stored reflections."""
        return len(self.reflections)

    def is_empty(self) -> bool:
        """Check if memory has no reflections."""
        return len(self.reflections) == 0

    def is_full(self) -> bool:
        """Check if memory is at max capacity."""
        return len(self.reflections) >= self.max_size

    def __len__(self) -> int:
        return len(self.reflections)

    def __repr__(self) -> str:
        return f"EpisodicMemory(size={len(self.reflections)}/{self.max_size})"

    def __str__(self) -> str:
        return self.get_formatted()
