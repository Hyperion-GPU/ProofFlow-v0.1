"""Tests for the policy gate dry-run pipeline orchestrator."""

from __future__ import annotations

import inspect
import json

import pytest

from proofflow.services.policy_gate_action_snapshot import (
    PolicyGateActionSnapshot,
    stable_preview_hash,
)
from proofflow.services.policy_gate_dry_run_pipeline import evaluate_dry_run_pipeline
from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateEvaluation,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
)


def _allow_result() -> PolicyGateResult:
    return PolicyGateResult(
        policy_id="test-allow",
        policy_name="Test Allow",
        category=PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
        severity=PolicySeverity.INFO,
        outcome=PolicyOutcome.ALLOW,
        reason="test allow",
    )


def _block_result() -> PolicyGateResult:
    return PolicyGateResult(
        policy_id="test-block",
        policy_name="Test Block",
        category=PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
        severity=PolicySeverity.HIGH,
        outcome=PolicyOutcome.BLOCK,
        reason="test block",
    )


def _warn_result() -> PolicyGateResult:
    return PolicyGateResult(
        policy_id="test-warn",
        policy_name="Test Warn",
        category=PolicyCategory.NETWORK_EXECUTION,
        severity=PolicySeverity.MEDIUM,
        outcome=PolicyOutcome.WARN,
        reason="test warn",
    )


class TestHappyPathHighRisk:
    def test_destructive_action_with_full_context(self):
        preview = {"from_path": "/tmp/a.txt", "to_path": "/tmp/b.txt"}
        snapshot = PolicyGateActionSnapshot(
            action_type="delete_file",
            case_id="case-1",
            action_id="action-1",
            preview=preview,
            undo={"restore_path": "/tmp/a.txt"},
        )
        evaluation = PolicyGateEvaluation(results=(_block_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-1",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.high_risk is True
        assert result.context_bound is True
        assert result.would_have_outcome == PolicyOutcome.BLOCK
        assert result.recommended_for_review is True
        assert result.non_enforcing is True
        assert result.label == "observed_only"


class TestHappyPathHarmless:
    def test_harmless_action_with_allow(self):
        preview = {"description": "read-only check"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect_file",
            case_id="case-2",
            action_id="action-2",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-2",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.high_risk is False
        assert result.context_bound is True
        assert result.would_have_outcome == PolicyOutcome.ALLOW
        assert result.recommended_for_review is False
        assert result.non_enforcing is True


class TestMissingContext:
    def test_no_case_id_fails_closed(self):
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            action_id="action-3",
            preview={"path": "/tmp/x"},
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(snapshot, evaluation)

        assert result.context_bound is False
        assert result.would_have_outcome == PolicyOutcome.FAIL_CLOSED
        assert result.recommended_for_review is True

    def test_no_action_id_fails_closed(self):
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-4",
            preview={"path": "/tmp/x"},
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(snapshot, evaluation)

        assert result.context_bound is False
        assert result.would_have_outcome == PolicyOutcome.FAIL_CLOSED

    def test_no_preview_hash_fails_closed(self):
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-5",
            action_id="action-5",
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(snapshot, evaluation)

        assert result.context_bound is False
        assert result.would_have_outcome == PolicyOutcome.FAIL_CLOSED


class TestContextMismatch:
    def test_action_id_mismatch_fails_closed(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-6",
            action_id="action-6",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="different-action-id",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.context_bound is False
        assert result.would_have_outcome == PolicyOutcome.FAIL_CLOSED

    def test_preview_hash_mismatch_fails_closed(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-7",
            action_id="action-7",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-7",
            expected_preview_hash="0000000000000000000000000000000000000000000000000000000000000000",
        )

        assert result.context_bound is False
        assert result.would_have_outcome == PolicyOutcome.FAIL_CLOSED


class TestEmptyEvaluation:
    def test_empty_results_fail_closed(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-8",
            action_id="action-8",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=())

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-8",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.would_have_outcome == PolicyOutcome.FAIL_CLOSED
        assert result.context_bound is True


class TestBlockPropagation:
    def test_block_outcome_propagates(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-9",
            action_id="action-9",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_block_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-9",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.would_have_outcome == PolicyOutcome.BLOCK
        assert result.context_bound is True


class TestCommandClassification:
    def test_network_command_classified(self):
        preview = {"info": "fetch"}
        snapshot = PolicyGateActionSnapshot(
            action_type="run_command",
            case_id="case-10",
            action_id="action-10",
            preview=preview,
            affected_commands=("curl https://example.invalid",),
        )
        evaluation = PolicyGateEvaluation(results=(_warn_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-10",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.high_risk is True
        categories = result.observation.classification.categories
        assert PolicyCategory.NETWORK_EXECUTION in categories

    def test_package_command_classified(self):
        preview = {"info": "install"}
        snapshot = PolicyGateActionSnapshot(
            action_type="run_command",
            case_id="case-11",
            action_id="action-11",
            preview=preview,
            affected_commands=("pip install requests",),
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-11",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.high_risk is True
        categories = result.observation.classification.categories
        assert PolicyCategory.PACKAGE_DEPENDENCY_MUTATION in categories

    def test_persistence_command_classified(self):
        preview = {"info": "schedule"}
        snapshot = PolicyGateActionSnapshot(
            action_type="run_command",
            case_id="case-12",
            action_id="action-12",
            preview=preview,
            affected_commands=("schtasks /create /tn test",),
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-12",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.high_risk is True
        categories = result.observation.classification.categories
        assert PolicyCategory.PROCESS_PERSISTENCE in categories

    def test_multi_category_commands(self):
        preview = {"info": "multi"}
        snapshot = PolicyGateActionSnapshot(
            action_type="run_command",
            case_id="case-13",
            action_id="action-13",
            preview=preview,
            affected_commands=(
                "curl https://example.invalid/pkg.tar.gz",
                "pip install ./pkg.tar.gz",
            ),
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-13",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.high_risk is True
        categories = result.observation.classification.categories
        assert PolicyCategory.NETWORK_EXECUTION in categories
        assert PolicyCategory.PACKAGE_DEPENDENCY_MUTATION in categories


class TestMissingInvariants:
    def test_destructive_without_undo(self):
        preview = {"from_path": "/tmp/a.txt"}
        snapshot = PolicyGateActionSnapshot(
            action_type="delete_file",
            case_id="case-14",
            action_id="action-14",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-14",
            expected_preview_hash=stable_preview_hash(preview),
        )

        missing = result.observation.classification.missing_invariants
        assert "missing_undo" in missing

    def test_high_risk_without_preview(self):
        snapshot = PolicyGateActionSnapshot(
            action_type="delete_file",
            case_id="case-15",
            action_id="action-15",
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(snapshot, evaluation)

        missing = result.observation.classification.missing_invariants
        assert "missing_preview" in missing


class TestFrozenInstance:
    def test_cannot_mutate_result(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect",
            case_id="case-16",
            action_id="action-16",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-16",
            expected_preview_hash=stable_preview_hash(preview),
        )

        with pytest.raises(AttributeError):
            result.pipeline_id = "mutated"  # type: ignore[misc]


class TestAliasSafety:
    def test_mutating_to_dict_does_not_affect_result(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect",
            case_id="case-17",
            action_id="action-17",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-17",
            expected_preview_hash=stable_preview_hash(preview),
            pipeline_id="pipe-1",
        )

        output = result.to_dict()
        output["pipeline_id"] = "mutated"
        output["would_have_outcome"] = "mutated"

        assert result.pipeline_id == "pipe-1"
        assert result.would_have_outcome == PolicyOutcome.ALLOW


class TestJsonSerialization:
    def test_to_dict_is_json_safe(self):
        preview = {"info": "test", "nested": {"key": [1, 2, 3]}}
        snapshot = PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-18",
            action_id="action-18",
            preview=preview,
            affected_commands=("curl https://example.invalid",),
        )
        evaluation = PolicyGateEvaluation(results=(_warn_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-18",
            expected_preview_hash=stable_preview_hash(preview),
            pipeline_id="pipe-2",
            observation_id="obs-1",
        )

        payload = result.to_dict()
        serialized = json.dumps(payload)
        assert isinstance(serialized, str)
        assert len(serialized) > 0


class TestNoAuthorityFields:
    def test_top_level_keys_have_no_authority(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect",
            case_id="case-19",
            action_id="action-19",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-19",
            expected_preview_hash=stable_preview_hash(preview),
        )

        payload = result.to_dict()
        authority_keys = {
            "allow_execution",
            "block_execution",
            "blocked_execution",
            "final_outcome",
            "is_blocking",
            "requires_operator_decision",
        }
        top_level_keys = set(payload.keys())
        assert top_level_keys.isdisjoint(authority_keys)


class TestNoRuntimeImports:
    def test_pipeline_module_does_not_import_runtime(self):
        import proofflow.services.policy_gate_dry_run_pipeline as mod

        source = inspect.getsource(mod)
        forbidden = [
            "proofflow.routers",
            "proofflow.db",
            "proofflow.migrations",
            "proofflow.services.action_service",
            "proofflow.services.backup_service",
            "proofflow.services.restore_service",
        ]
        for name in forbidden:
            assert name not in source, f"pipeline imports runtime module: {name}"


class TestSnapshotIdentity:
    def test_result_preserves_snapshot_reference(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect",
            case_id="case-20",
            action_id="action-20",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(snapshot, evaluation)

        assert result.snapshot is snapshot


class TestIdPropagation:
    def test_pipeline_id_propagates(self):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect",
            case_id="case-21",
            action_id="action-21",
            preview=preview,
        )
        evaluation = PolicyGateEvaluation(results=(_allow_result(),))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            pipeline_id="pipe-3",
            observation_id="obs-2",
        )

        assert result.pipeline_id == "pipe-3"
        assert result.to_dict()["pipeline_id"] == "pipe-3"
        assert result.observation.observation_id == "obs-2"
        assert result.to_dict()["observation"]["observation_id"] == "obs-2"


class TestParametrizedOutcomes:
    @pytest.mark.parametrize(
        "outcome",
        [
            PolicyOutcome.ALLOW,
            PolicyOutcome.WARN,
            PolicyOutcome.REQUIRE_DECISION,
            PolicyOutcome.BLOCK,
            PolicyOutcome.FAIL_CLOSED,
        ],
    )
    def test_outcome_delegation(self, outcome: PolicyOutcome):
        preview = {"info": "test"}
        snapshot = PolicyGateActionSnapshot(
            action_type="inspect",
            case_id="case-param",
            action_id="action-param",
            preview=preview,
        )
        result_item = PolicyGateResult(
            policy_id="test-param",
            policy_name="Test Param",
            category=PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
            severity=PolicySeverity.MEDIUM,
            outcome=outcome,
            reason="parametrized test",
        )
        evaluation = PolicyGateEvaluation(results=(result_item,))

        result = evaluate_dry_run_pipeline(
            snapshot,
            evaluation,
            expected_action_id="action-param",
            expected_preview_hash=stable_preview_hash(preview),
        )

        assert result.would_have_outcome == outcome
        assert result.non_enforcing is True
        assert result.label == "observed_only"
