# -*- coding: utf-8 -*-
"""
Experiment Configurations - Phase 6
====================================

Defines ablation configurations and model configurations.
"""

from dataclasses import dataclass
from typing import List


# =============================================================================
# ABLATION CONFIGURATIONS
# =============================================================================

@dataclass
class AblationConfig:
    """Ablation configuration."""
    name: str
    max_trials: int
    reflection_enabled: bool
    description: str


BASELINE = AblationConfig(
    name="baseline",
    max_trials=1,
    reflection_enabled=False,
    description="No reflection, single attempt"
)

FULL_REFLEXION = AblationConfig(
    name="full_reflexion",
    max_trials=2,
    reflection_enabled=True,
    description="Full Reflexion with memory"
)

TWO_TRY_NO_REFLECTION = AblationConfig(
    name="two_try_no_reflection",
    max_trials=2,
    reflection_enabled=False,
    description="Two attempts without reflection (ablation control)"
)

ALL_ABLATION_CONFIGS: List[AblationConfig] = [BASELINE, FULL_REFLEXION, TWO_TRY_NO_REFLECTION]


# =============================================================================
# MODEL CONFIGURATIONS
# =============================================================================

@dataclass
class ModelConfig:
    """Model configuration with pricing."""
    name: str
    model_id: str
    input_cost_per_million: float
    output_cost_per_million: float


HAIKU_30 = ModelConfig(
    name="haiku30",
    model_id="claude-3-haiku-20240307",
    input_cost_per_million=0.25,
    output_cost_per_million=1.25
)

HAIKU_35 = ModelConfig(
    name="haiku35",
    model_id="claude-3-5-haiku-20241022",
    input_cost_per_million=1.0,
    output_cost_per_million=5.0
)

HAIKU_45 = ModelConfig(
    name="haiku45",
    model_id="claude-haiku-4-5-20251001",
    input_cost_per_million=1.0,
    output_cost_per_million=5.0
)

SONNET_45 = ModelConfig(
    name="sonnet45",
    model_id="claude-sonnet-4-5-20250929",
    input_cost_per_million=3.0,
    output_cost_per_million=15.0
)

OPUS_45 = ModelConfig(
    name="opus45",
    model_id="claude-opus-4-5-20251101",
    input_cost_per_million=5.0,
    output_cost_per_million=25.0
)

ALL_MODEL_CONFIGS: List[ModelConfig] = [HAIKU_30, HAIKU_35, HAIKU_45, SONNET_45, OPUS_45]


# =============================================================================
# TEST CASES
# =============================================================================

@dataclass
class TestCase:
    """Test case definition."""
    case_id: str
    name: str
    namespace: str
    pod_pattern: str
    difficulty: str
    requires_connectivity_check: bool = False  # Only for cases where pod runs but service fails


TEST_CASES: List[TestCase] = [
    # Single-bug cases (Phase 6 - Baseline)
    TestCase("case1", "Wrong Port", "case1-test", "wrong-port-*", "easy", requires_connectivity_check=True),
    TestCase("case2", "Incorrect Selector", "case2-test", "myapp-deployment-*", "easy"),
    TestCase("case3", "Liveness Probe", "case3-test", "liveness-probe-*", "medium"),
    TestCase("case4", "Wrong Interface", "case4-test", "wrong-interface-*", "hard", requires_connectivity_check=True),
    TestCase("case5", "Port Mismatch", "case5-test", "port-mismatch-*", "hard", requires_connectivity_check=True),
    TestCase("case6", "Misspelling", "case6-test", "misspelling-deployment-*", "easy"),
    TestCase("case7", "Volume Mount", "case7-test", "volume-mount-*", "medium"),
    TestCase("case8", "Environment Variable", "case8-test", "env-*", "medium"),
    # Multi-bug cases (Phase 8 - Reflexion benefit test)
    TestCase("case9", "Double Trouble (2 bugs)", "case12-double", "backend-*", "hard", requires_connectivity_check=True),
    TestCase("case10", "Triple Threat (3 bugs)", "case13-triple", "webapp-*", "very_hard", requires_connectivity_check=True),
    TestCase("case11", "ConfigMap + Selector (2 bugs)", "case11-configmap-selector", "webapp-*", "hard", requires_connectivity_check=True),
]

# Case ID to folder mapping
CASE_FOLDER_MAPPING = {
    "case1": "1_wrong_port",
    "case2": "2_incorrect_selector",
    "case3": "3_liveness_probe",
    "case4": "4_wrong_interface",
    "case5": "5_port_mismatch",
    "case6": "6_misspelling",
    "case7": "7_volume_mount",
    "case8": "8_environment_variable",
    "case9": "9_double_trouble",
    "case10": "10_triple_threat",
    "case11": "11_configmap_selector",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_ablation_config(name: str) -> AblationConfig:
    """Get ablation config by name."""
    configs = {c.name: c for c in ALL_ABLATION_CONFIGS}
    if name not in configs:
        raise ValueError(f"Unknown config: {name}")
    return configs[name]


def get_model_config(name: str) -> ModelConfig:
    """Get model config by name."""
    models = {m.name: m for m in ALL_MODEL_CONFIGS}
    if name not in models:
        raise ValueError(f"Unknown model: {name}")
    return models[name]


def get_test_case(case_id: str) -> TestCase:
    """Get test case by ID."""
    cases = {c.case_id: c for c in TEST_CASES}
    if case_id not in cases:
        raise ValueError(f"Unknown case: {case_id}")
    return cases[case_id]
