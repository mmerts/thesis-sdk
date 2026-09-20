# -*- coding: utf-8 -*-
"""two_try_feedback bypass testi - LLM'siz, fake actor/evaluator ile."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from core.reflexion_loop import ReflexionLoop


class FakeActor:
    def __init__(self):
        self.received_memory = []

    async def generate_trajectory(self, pod_name, namespace="default", memory=None):
        self.received_memory.append(list(memory) if memory else None)
        return "fake trajectory", {"commands": [], "cost_usd": 0.0, "usage": {}}


class FakeEvaluator:
    async def evaluate(self, pod_name, namespace="default", wait_time=5,
                       requires_connectivity_check=False, settle_s=0):
        return {"success": False, "pod_status": "CrashLoopBackOff",
                "reason": "Pod not ready"}, {}


def test_feedback_only_bypass():
    loop = ReflexionLoop(max_trials=2, reflection_enabled=False,
                         feedback_only=True, model="claude-haiku-4-5-20251001")
    fake_actor = FakeActor()
    loop.actor = fake_actor
    loop.evaluator = FakeEvaluator()

    result = asyncio.run(loop.run("fake-pod", "fake-ns"))

    assert loop.reflector is None, "feedback modunda reflection LLM olmamali"
    assert result.total_trials == 2, f"2 trial beklenirdi, {result.total_trials} geldi"
    assert fake_actor.received_memory[0] is None, "trial 1 memory'siz baslamali"
    mem2 = fake_actor.received_memory[1]
    assert mem2 is not None and len(mem2) == 1, "trial 2 tek feedback almali"
    expected = ("The previous attempt failed. Evaluator feedback: Pod not ready "
                "(Pod status: CrashLoopBackOff)")
    assert mem2[0] == expected, f"feedback string farkli: {mem2[0]!r}"
    assert result.trials[0].reflection_content == expected
    assert result.trials[0].reflection_cost == 0.0, "feedback kolu LLM maliyeti uretmemeli"
    print("[PASS] test_feedback_only_bypass")


def test_two_try_no_reflection_unchanged():
    loop = ReflexionLoop(max_trials=2, reflection_enabled=False,
                         model="claude-haiku-4-5-20251001")
    fake_actor = FakeActor()
    loop.actor = fake_actor
    loop.evaluator = FakeEvaluator()

    asyncio.run(loop.run("fake-pod", "fake-ns"))

    assert fake_actor.received_memory == [None, None], "two_try kolu memory almamali"
    print("[PASS] test_two_try_no_reflection_unchanged")


class FakeReflector:
    def __init__(self):
        self.received_evaluation = []

    async def reflect(self, pod_name, trajectory, evaluation, memory=None):
        self.received_evaluation.append(dict(evaluation))
        return "fake reflection", {}


def _run_reflexion(reflection_feedback):
    loop = ReflexionLoop(max_trials=2, reflection_enabled=True,
                         reflection_feedback=reflection_feedback,
                         model="claude-haiku-4-5-20251001")
    fake_actor, fake_reflector = FakeActor(), FakeReflector()
    loop.actor = fake_actor
    loop.evaluator = FakeEvaluator()
    loop.reflector = fake_reflector
    asyncio.run(loop.run("fake-pod", "fake-ns"))
    return fake_actor, fake_reflector


def test_reflection_feedback_passes_reason():
    actor, reflector = _run_reflexion(reflection_feedback=True)
    assert reflector.received_evaluation == [
        {"pod_status": "CrashLoopBackOff", "reason": "Pod not ready"}
    ], f"reflector reason almali: {reflector.received_evaluation!r}"
    assert actor.received_memory[1] == ["fake reflection"], "actor yalniz reflection almali"
    print("[PASS] test_reflection_feedback_passes_reason")


def test_full_reflexion_unchanged():
    actor, reflector = _run_reflexion(reflection_feedback=False)
    assert reflector.received_evaluation == [{"pod_status": "CrashLoopBackOff"}],         f"varsayilan full_reflexion reason ALMAMALI: {reflector.received_evaluation!r}"
    assert actor.received_memory[1] == ["fake reflection"]
    print("[PASS] test_full_reflexion_unchanged")


if __name__ == "__main__":
    test_feedback_only_bypass()
    test_two_try_no_reflection_unchanged()
    test_reflection_feedback_passes_reason()
    test_full_reflexion_unchanged()
    print("\nTUM TESTLER GECTI")
