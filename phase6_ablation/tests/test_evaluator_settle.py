# -*- coding: utf-8 -*-
"""Evaluator stabilizasyon penceresi testi - kubectl'siz, scripted _evaluate_pod ile."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from core.agents import evaluator as ev
from core.agents.evaluator import ProgrammaticEvaluator, EvaluationResult


def _res(ok, reason, status="Pending"):
    return EvaluationResult(success=ok, reason=reason, pod_status=status,
                            pod_ready="N/A", details={})


def _run(sequence, settle_s):
    """sequence: _evaluate_pod'un sirayla dondurecegi sonuclar. Saat sahte: her sleep 5 sn ilerletir."""
    e = ProgrammaticEvaluator()
    calls = []
    clock = [0.0]

    async def fake_eval(*a, **k):
        calls.append(1)
        return sequence[min(len(calls) - 1, len(sequence) - 1)]

    async def fake_sleep(s):
        clock[0] += s

    e._evaluate_pod = fake_eval
    real_sleep, real_mono = ev.asyncio.sleep, ev.time.monotonic
    ev.asyncio.sleep, ev.time.monotonic = fake_sleep, lambda: clock[0]
    try:
        loop = asyncio.new_event_loop()
        out, _ = loop.run_until_complete(e.evaluate("p", "ns", wait_time=5, settle_s=settle_s))
        loop.close()
    finally:
        ev.asyncio.sleep, ev.time.monotonic = real_sleep, real_mono
    return out, len(calls)


def test_default_is_single_sample():
    out, n = _run([_res(False, "Pod is in Pending phase, not Running")], settle_s=0)
    assert n == 1 and out["samples"] == 1 and out["success"] is False
    assert out["first_success"] is False and out["first_reason"] == out["reason"]
    print("[PASS] test_default_is_single_sample")


def test_recovers_inside_window():
    seq = [_res(False, "Pod is in Pending phase, not Running"),
           _res(False, "Not all containers ready: 0/1", "Running"),
           _res(True, "Pod is Running with all containers ready (1/1)", "Running")]
    out, n = _run(seq, settle_s=90)
    assert n == 3 and out["samples"] == 3 and out["success"] is True
    assert out["first_success"] is False and out["first_pod_status"] == "Pending"
    assert out["settle_elapsed"] == 10.0
    print("[PASS] test_recovers_inside_window")


def test_stops_on_port_fault():
    out, n = _run([_res(False, "Service 'svc' not responding on port 80", "Running")], settle_s=90)
    assert n == 1 and out["success"] is False
    print("[PASS] test_stops_on_port_fault")


def test_window_is_bounded():
    out, n = _run([_res(False, "Pod is in Pending phase, not Running")], settle_s=90)
    assert out["success"] is False
    assert n == 19, n  # first sample at t=0 of the window, then every 5 s up to 90 s
    assert out["settle_elapsed"] == 90.0
    print("[PASS] test_window_is_bounded")


def test_first_success_needs_no_polling():
    out, n = _run([_res(True, "ok", "Running")], settle_s=90)
    assert n == 1 and out["first_success"] is True
    print("[PASS] test_first_success_needs_no_polling")


if __name__ == "__main__":
    test_default_is_single_sample()
    test_recovers_inside_window()
    test_stops_on_port_fault()
    test_window_is_bounded()
    test_first_success_needs_no_polling()
    print("\nTUM TESTLER GECTI")
