# -*- coding: utf-8 -*-
"""baseline_self_verify config testi - LLM'siz, prompt/config dogrulama."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from core.configs.experiment_configs import get_ablation_config
from core.agents.actor import ActorAgent
from core.reflexion_loop import ReflexionLoop


def test_config_exists():
    cfg = get_ablation_config("baseline_self_verify")
    assert cfg.max_trials == 1, "tek trial olmali"
    assert cfg.reflection_enabled is False
    assert cfg.feedback_only is False
    assert cfg.self_verify is True
    print("[PASS] test_config_exists")


def test_baseline_config_unchanged():
    cfg = get_ablation_config("baseline")
    assert getattr(cfg, "self_verify", False) is False
    print("[PASS] test_baseline_config_unchanged")


def test_actor_default_prompt_forbids_verify():
    actor = ActorAgent()
    assert "Do NOT verify" in actor.system_prompt
    assert "Do NOT enter retry loops" in actor.system_prompt
    print("[PASS] test_actor_default_prompt_forbids_verify")


def test_actor_self_verify_prompt_allows_verify():
    actor = ActorAgent(self_verify=True)
    sp = actor.system_prompt
    assert "Do NOT verify" not in sp, "self_verify promptunda verify yasagi olmamali"
    assert "Do NOT enter retry loops" not in sp
    assert "Do NOT run verification" not in sp
    assert "PHASE 3: VERIFY" in sp, "verify fazi tanimlanmali"
    assert "kubectl edit" in sp, "FORBIDDEN blok korunmali"
    assert "FIX COMPLETE" in sp
    print("[PASS] test_actor_self_verify_prompt_allows_verify")


def test_build_prompt_variants():
    default_p = ActorAgent()._build_prompt("pod-x", "ns-x", None)
    sv_p = ActorAgent(self_verify=True)._build_prompt("pod-x", "ns-x", None)
    assert "(do not verify)" in default_p
    assert "do not verify" not in sv_p.lower()
    assert "VERIFY" in sv_p
    print("[PASS] test_build_prompt_variants")


def test_loop_passes_flag_to_actor():
    loop = ReflexionLoop(max_trials=1, reflection_enabled=False,
                         self_verify=True, model="claude-haiku-4-5-20251001")
    assert loop.actor.self_verify is True
    default_loop = ReflexionLoop(max_trials=1, reflection_enabled=False,
                                 model="claude-haiku-4-5-20251001")
    assert default_loop.actor.self_verify is False
    print("[PASS] test_loop_passes_flag_to_actor")


if __name__ == "__main__":
    test_config_exists()
    test_baseline_config_unchanged()
    test_actor_default_prompt_forbids_verify()
    test_actor_self_verify_prompt_allows_verify()
    test_build_prompt_variants()
    test_loop_passes_flag_to_actor()
    print("\nTUM TESTLER GECTI")
