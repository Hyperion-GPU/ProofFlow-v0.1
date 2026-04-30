import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

import proofflow.services.policy_gate_action_classifier as classifier_module
from proofflow.services.policy_gate_action_classifier import (
    PolicyGateActionClassification,
    PolicyGateActionSurface,
    classify_policy_gate_action,
)
from proofflow.services.policy_gate_service import PolicyCategory


AUTHORITY_FIELDS = {
    "allow_execution",
    "block_execution",
    "blocked_execution",
    "final_outcome",
    "would_have_outcome",
    "is_blocking",
    "requires_operator_decision",
}


def test_destructive_local_action_is_classified_high_risk():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="delete_file",
            is_destructive=True,
            has_preview=True,
            has_undo=True,
        )
    )

    assert classification.high_risk is True
    assert classification.recommended_dry_run is True
    assert classification.categories == (
        PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
    )
    assert classification.reasons == ("destructive_action",)
    assert classification.missing_invariants == ()


def test_restore_related_surface_is_classified_high_risk():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="restore_to_new_location",
            is_restore_related=True,
            has_preview=True,
        )
    )

    assert classification.high_risk is True
    assert PolicyCategory.BACKUP_RESTORE_TARGET_RISK in classification.categories
    assert "restore_related_action" in classification.reasons


@pytest.mark.parametrize(
    ("command", "expected_category", "expected_reason"),
    [
        (
            "curl https://example.invalid/install.ps1",
            PolicyCategory.NETWORK_EXECUTION,
            "network_command_surface",
        ),
        (
            "python -m pip install risky-package",
            PolicyCategory.PACKAGE_DEPENDENCY_MUTATION,
            "package_dependency_command_surface",
        ),
        (
            "schtasks /Create /SC ONLOGON /TN ProofFlowTask",
            PolicyCategory.PROCESS_PERSISTENCE,
            "process_persistence_command_surface",
        ),
    ],
)
def test_command_surfaces_are_classified_high_risk(
    command,
    expected_category,
    expected_reason,
):
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="run_command",
            affected_commands=[command],
            has_preview=True,
        )
    )

    assert classification.high_risk is True
    assert classification.recommended_dry_run is True
    assert expected_category in classification.categories
    assert expected_reason in classification.reasons


def test_harmless_read_only_surface_is_not_high_risk():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="read_status",
            action_category="read_only",
            affected_paths=["D:/ProofFlow v0.1/README.md"],
            has_preview=True,
            has_source_reference=True,
        )
    )

    assert classification.high_risk is False
    assert classification.recommended_dry_run is False
    assert classification.categories == ()
    assert classification.reasons == ()
    assert classification.missing_invariants == ()


def test_missing_preview_on_high_risk_surface_is_recorded_as_invariant_only():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="run_command",
            affected_commands=["Invoke-WebRequest https://example.invalid"],
        )
    )

    payload = classification.to_dict()

    assert classification.high_risk is True
    assert "missing_preview" in classification.missing_invariants
    assert payload["missing_invariants"] == ["missing_preview"]
    assert not AUTHORITY_FIELDS.intersection(payload)


def test_destructive_surface_without_undo_records_missing_undo():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="delete_file",
            is_destructive=True,
            has_preview=True,
            has_undo=False,
        )
    )

    assert classification.high_risk is True
    assert "missing_undo" in classification.missing_invariants
    assert "missing_preview" not in classification.missing_invariants


@pytest.mark.parametrize(
    "surface",
    [
        PolicyGateActionSurface(
            action_type="write_artifact",
            action_category="artifact",
        ),
        PolicyGateActionSurface(
            action_type="write_artifact",
            metadata={"artifact_backed": True},
        ),
    ],
)
def test_artifact_backed_surface_without_source_records_missing_source(surface):
    classification = classify_policy_gate_action(surface)

    assert "missing_source_reference" in classification.missing_invariants
    assert classification.high_risk is False
    assert classification.recommended_dry_run is False


def test_code_workflow_without_test_evidence_records_missing_test_evidence():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="code_patch",
            is_code_workflow=True,
            has_source_reference=True,
            has_test_evidence=False,
        )
    )

    assert classification.high_risk is False
    assert classification.recommended_dry_run is False
    assert classification.missing_invariants == ("missing_test_evidence",)


def test_classification_serializes_to_json_safe_non_authoritative_payload():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="restore_and_install",
            is_restore_related=True,
            affected_commands=["npm install"],
            has_preview=True,
        )
    )

    payload = classification.to_dict()
    json.dumps(payload)

    assert payload["high_risk"] is True
    assert payload["recommended_dry_run"] is True
    assert payload["non_authoritative"] is True
    assert payload["categories"] == [
        "backup_restore_target_risk",
        "package_dependency_mutation",
    ]
    assert not AUTHORITY_FIELDS.intersection(payload)


def test_surface_and_classification_are_alias_safe():
    paths = ["D:/ProofFlow v0.1/backend/proofflow/services/action_service.py"]
    commands = ["curl https://example.invalid"]
    metadata = {"artifact_backed": True, "tags": ["source"]}
    surface = PolicyGateActionSurface(
        action_type="write_artifact",
        affected_paths=paths,
        affected_commands=commands,
        metadata=metadata,
        has_preview=True,
    )

    paths.append("D:/mutated")
    commands.append("npm install mutated")
    metadata["artifact_backed"] = False
    metadata["tags"].append("mutated")

    assert surface.affected_paths == (
        "D:/ProofFlow v0.1/backend/proofflow/services/action_service.py",
    )
    assert surface.affected_commands == ("curl https://example.invalid",)
    assert surface.metadata["artifact_backed"] is True
    assert surface.metadata["tags"] == ("source",)

    classification = classify_policy_gate_action(surface)
    assert classification.categories == (PolicyCategory.NETWORK_EXECUTION,)

    payload = surface.to_dict()
    payload["affected_paths"].append("D:/payload-mutated")
    payload["affected_commands"].append("payload command")
    payload["metadata"]["artifact_backed"] = False
    payload["metadata"]["tags"].append("payload-mutated")

    assert surface.affected_paths == (
        "D:/ProofFlow v0.1/backend/proofflow/services/action_service.py",
    )
    assert surface.affected_commands == ("curl https://example.invalid",)
    assert surface.metadata["artifact_backed"] is True
    assert surface.metadata["tags"] == ("source",)

    classification_payload = classification.to_dict()
    classification_payload["categories"].append("mutated")
    classification_payload["missing_invariants"].append("mutated")

    assert classification.categories == (PolicyCategory.NETWORK_EXECUTION,)
    assert classification.missing_invariants == ("missing_source_reference",)


def test_classification_constructor_collections_are_alias_safe():
    categories = [PolicyCategory.SECRET_ACCESS]
    reasons = ["secret_access_surface"]
    missing = ["missing_preview"]
    classification = PolicyGateActionClassification(
        high_risk=True,
        categories=categories,
        reasons=reasons,
        missing_invariants=missing,
        recommended_dry_run=True,
    )

    categories.append(PolicyCategory.NETWORK_EXECUTION)
    reasons.append("network_command_surface")
    missing.append("missing_undo")

    assert classification.categories == (PolicyCategory.SECRET_ACCESS,)
    assert classification.reasons == ("secret_access_surface",)
    assert classification.missing_invariants == ("missing_preview",)


def test_classifier_does_not_expose_policy_decision_or_authority_fields():
    classification = classify_policy_gate_action(
        PolicyGateActionSurface(
            action_type="read_status",
            has_preview=True,
        )
    )
    payload = classification.to_dict()

    assert not AUTHORITY_FIELDS.intersection(payload)
    assert not AUTHORITY_FIELDS.intersection(PolicyGateActionClassification.__annotations__)
    assert "PolicyOutcome" not in vars(classifier_module)
    assert "PolicyGateEvaluation" not in vars(classifier_module)
    assert "PolicyGateDryRunEvaluation" not in vars(classifier_module)
    assert "PolicyOutcome" not in inspect.getsource(classifier_module)


def test_surface_and_classification_are_frozen():
    surface = PolicyGateActionSurface(action_type="read_status")
    classification = classify_policy_gate_action(surface)

    with pytest.raises(FrozenInstanceError):
        surface.action_type = "mutated"

    with pytest.raises(FrozenInstanceError):
        classification.high_risk = True
