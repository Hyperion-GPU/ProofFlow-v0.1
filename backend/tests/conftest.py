"""Shared test fixtures.

The policy gate enforcement (Checkpoint H) pauses high-risk filesystem actions
at pending_decision. Tests that are NOT specifically testing enforcement behavior
use this autouse fixture to bypass the gate so they can test their own concerns
(action lifecycle, undo, safety, etc.) without interference.

Tests in test_policy_gate_enforcement.py and test_policy_gate_runtime_observer.py
override this by setting the _bypass_policy_gate marker to False.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _bypass_policy_gate(request):
    """Bypass the policy gate for tests that don't test enforcement.

    Tests that DO test enforcement should mark themselves with:
        @pytest.mark.no_bypass_policy_gate
    """
    if request.node.get_closest_marker("no_bypass_policy_gate"):
        yield
        return

    # Check if the test module is one that tests enforcement directly
    module_file = getattr(request.node.module, "__file__", "") or ""
    enforcement_files = (
        "test_policy_gate_enforcement",
        "test_policy_gate_runtime_observer",
        "test_policy_gate_observation_ui",
    )
    if any(name in module_file for name in enforcement_files):
        yield
        return

    with patch(
        "proofflow.services.action_service._check_policy_gate",
        return_value=None,
    ):
        yield
