import inspect
import json
from dataclasses import FrozenInstanceError, dataclass
from enum import Enum
from pathlib import Path

import pytest

import proofflow.services.policy_gate_action_snapshot as snapshot_module
from proofflow.services.policy_gate_action_snapshot import (
    PolicyGateActionSnapshot,
    action_snapshot_to_context,
    action_snapshot_to_surface,
    stable_preview_hash,
)
from proofflow.services.policy_gate_dry_run_context import bind_dry_run_context
from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateEvaluation,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
)


AUTHORITY_FIELDS = {
    "allow_execution",
    "block_execution",
    "blocked_execution",
    "final_outcome",
    "would_have_outcome",
    "is_blocking",
    "requires_operator_decision",
}

RUNTIME_IMPORT_MARKERS = {
    "proofflow.routers",
    "proofflow.db",
    "proofflow.migrations",
    "proofflow.services.action_service",
    "proofflow.services.restore_service",
    "proofflow.services.report_service",
    "frontend",
}


class _SampleEnum(Enum):
    VALUE = "value"


@dataclass
class _SampleDataclass:
    value: str


def _policy_result(policy_id: str, outcome: PolicyOutcome) -> PolicyGateResult:
    return PolicyGateResult(
        policy_id=policy_id,
        policy_name=f"{policy_id} policy",
        category=PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
        severity=PolicySeverity.HIGH,
        outcome=outcome,
        reason=f"{outcome.value} result for snapshot adapter test.",
    )


def _evaluation(outcome: PolicyOutcome) -> PolicyGateEvaluation:
    return PolicyGateEvaluation(results=[_policy_result(outcome.value, outcome)])


def _contains_key_recursive(value, keys):
    if isinstance(value, dict):
        return any(
            key in keys or _contains_key_recursive(item, keys)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key_recursive(item, keys) for item in value)
    return False


def test_stable_preview_hash_ignores_dict_key_order():
    first = {
        "to_path": "D:/ProofFlow v0.1/output.txt",
        "from_path": "D:/ProofFlow v0.1/input.txt",
        "details": {"b": 2, "a": 1},
    }
    second = {
        "details": {"a": 1, "b": 2},
        "from_path": "D:/ProofFlow v0.1/input.txt",
        "to_path": "D:/ProofFlow v0.1/output.txt",
    }

    assert stable_preview_hash(first) == stable_preview_hash(second)


def test_stable_preview_hash_treats_tuple_and_list_deterministically():
    tuple_preview = {"paths": ("a.txt", "b.txt"), "steps": [1, 2]}
    list_preview = {"steps": [1, 2], "paths": ["a.txt", "b.txt"]}

    assert stable_preview_hash(tuple_preview) == stable_preview_hash(list_preview)


@pytest.mark.parametrize("preview", [None, {}, [], (), ""])
def test_stable_preview_hash_returns_none_for_missing_or_empty_preview(preview):
    assert stable_preview_hash(preview) is None


@pytest.mark.parametrize(
    "preview",
    [
        Path("D:/ProofFlow v0.1/README.md"),
        _SampleDataclass("value"),
        _SampleEnum.VALUE,
        object(),
        {1: "non-string-key"},
    ],
)
def test_stable_preview_hash_rejects_non_json_preview_objects(preview):
    with pytest.raises(TypeError):
        stable_preview_hash(preview)


def test_action_snapshot_to_context_maps_ids_preview_hash_and_expected_values():
    preview = {"from_path": "before.txt", "to_path": "after.txt"}
    expected_hash = stable_preview_hash(preview)
    context = action_snapshot_to_context(
        PolicyGateActionSnapshot(
            action_type="move_file",
            case_id="case-1",
            action_id="action-1",
            preview=preview,
        ),
        expected_action_id="action-1",
        expected_preview_hash=expected_hash,
        policy_evaluation_id="policy-eval-1",
    )

    assert context.case_id == "case-1"
    assert context.action_id == "action-1"
    assert context.preview_hash == expected_hash
    assert context.expected_action_id == "action-1"
    assert context.expected_preview_hash == expected_hash
    assert context.policy_evaluation_id == "policy-eval-1"


@pytest.mark.parametrize(
    ("expected_action_id", "expected_preview_hash", "mismatch_key"),
    [
        ("action-2", None, "action_id"),
        (None, "different-preview-hash", "preview_hash"),
    ],
)
def test_expected_mismatch_remains_visible_through_context_binding(
    expected_action_id,
    expected_preview_hash,
    mismatch_key,
):
    snapshot = PolicyGateActionSnapshot(
        action_type="read_status",
        case_id="case-1",
        action_id="action-1",
        preview={"path": "README.md"},
    )
    dry_run = bind_dry_run_context(
        _evaluation(PolicyOutcome.ALLOW),
        action_snapshot_to_context(
            snapshot,
            expected_action_id=expected_action_id,
            expected_preview_hash=expected_preview_hash,
        ),
    )

    assert dry_run.context_bound is False
    assert dry_run.context_mismatches == (mismatch_key,)
    assert dry_run.would_have_outcome == PolicyOutcome.FAIL_CLOSED


@pytest.mark.parametrize("action_type", ["move_file", "rename_file"])
def test_destructive_action_types_map_to_destructive_surface(action_type):
    surface = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type=action_type,
            preview={"from_path": "old.txt", "to_path": "new.txt"},
            undo={"kind": "move_back"},
        )
    )

    assert surface.is_destructive is True
    assert surface.has_preview is True
    assert surface.has_undo is True


@pytest.mark.parametrize(
    ("action_type", "action_category"),
    [("restore_backup", None), ("copy_file", "managed_restore")],
)
def test_restore_action_type_or_category_maps_to_restore_related_surface(
    action_type,
    action_category,
):
    surface = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type=action_type,
            action_category=action_category,
            preview={"target": "D:/restore-target"},
        )
    )

    assert surface.is_restore_related is True


def test_command_metadata_and_explicit_commands_populate_affected_commands():
    surface = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type="run_command",
            affected_commands=("schtasks /Create /TN ProofFlow",),
            metadata={
                "affected_commands": ["npm install"],
                "commands": ["curl https://example.invalid", "npm install"],
                "command": "Invoke-WebRequest https://example.invalid/bootstrap.ps1",
            },
            preview={"command": "preview"},
        )
    )

    assert surface.affected_commands == (
        "schtasks /Create /TN ProofFlow",
        "npm install",
        "curl https://example.invalid",
        "Invoke-WebRequest https://example.invalid/bootstrap.ps1",
    )


def test_preview_paths_metadata_paths_and_explicit_paths_populate_affected_paths():
    surface = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type="move_file",
            affected_paths=("explicit.txt",),
            metadata={"affected_paths": ["metadata.txt", "explicit.txt"]},
            preview={
                "from_path": "before.txt",
                "to_path": "after.txt",
                "dir_path": "D:/ProofFlow v0.1",
            },
        )
    )

    assert surface.affected_paths == (
        "explicit.txt",
        "metadata.txt",
        "before.txt",
        "after.txt",
        "D:/ProofFlow v0.1",
    )


def test_artifact_metadata_with_source_sets_source_reference():
    with_source = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type="write_artifact",
            action_category="artifact",
            metadata={"artifact_id": "artifact-1"},
            preview={"path": "artifact.md"},
        )
    )
    without_source = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type="write_artifact",
            action_category="artifact",
            preview={"path": "artifact.md"},
        )
    )

    assert with_source.has_source_reference is True
    assert without_source.has_source_reference is False


def test_code_workflow_with_and_without_test_evidence_maps_test_flag():
    with_tests = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type="code_patch",
            action_category="code_workflow",
            metadata={"test_command": "python -m pytest"},
            preview={"path": "backend/tests/test_policy_gate_service.py"},
        )
    )
    without_tests = action_snapshot_to_surface(
        PolicyGateActionSnapshot(
            action_type="code_patch",
            action_category="code_workflow",
            preview={"path": "backend/proofflow/services/policy_gate_service.py"},
        )
    )

    assert with_tests.is_code_workflow is True
    assert with_tests.has_test_evidence is True
    assert without_tests.is_code_workflow is True
    assert without_tests.has_test_evidence is False


def test_snapshot_and_adapter_outputs_are_json_safe_alias_safe_and_frozen():
    paths = ["README.md"]
    commands = ["curl https://example.invalid"]
    metadata = {"artifact_backed": True, "tags": ["proof"]}
    undo = {"steps": ["restore README.md"]}
    preview = {"path": "README.md", "details": {"version": 1}}
    snapshot = PolicyGateActionSnapshot(
        action_type="write_artifact",
        action_category="artifact",
        preview=preview,
        metadata=metadata,
        undo=undo,
        affected_paths=paths,
        affected_commands=commands,
    )
    original_preview_hash = stable_preview_hash(snapshot.preview)

    paths.append("mutated.txt")
    commands.append("npm install mutated")
    metadata["artifact_backed"] = False
    metadata["tags"].append("mutated")
    undo["steps"].append("mutated undo")
    preview["path"] = "mutated.txt"
    preview["details"]["version"] = 2

    assert snapshot.affected_paths == ("README.md",)
    assert snapshot.affected_commands == ("curl https://example.invalid",)
    assert snapshot.metadata["artifact_backed"] is True
    assert snapshot.metadata["tags"] == ("proof",)
    assert snapshot.undo["steps"] == ("restore README.md",)
    assert snapshot.preview["path"] == "README.md"
    assert snapshot.preview["details"]["version"] == 1
    assert stable_preview_hash(snapshot.preview) == original_preview_hash

    snapshot_payload = snapshot.to_dict()
    surface_payload = action_snapshot_to_surface(snapshot).to_dict()
    context_payload = action_snapshot_to_context(snapshot).to_dict()
    json.dumps(snapshot_payload)
    json.dumps(surface_payload)
    json.dumps(context_payload)

    snapshot_payload["metadata"]["tags"].append("payload-mutated")
    surface_payload["affected_paths"].append("payload-mutated")
    context_payload["case_id"] = "mutated"

    assert snapshot.metadata["tags"] == ("proof",)
    assert action_snapshot_to_surface(snapshot).affected_paths == ("README.md",)
    assert action_snapshot_to_context(snapshot).case_id is None

    with pytest.raises(FrozenInstanceError):
        snapshot.action_type = "mutated"


def test_adapter_payloads_do_not_include_execution_authority_fields():
    snapshot = PolicyGateActionSnapshot(
        action_type="read_status",
        case_id="case-1",
        action_id="action-1",
        preview={"path": "README.md"},
        metadata={
            "allow_execution": True,
            "final_outcome": "block",
            "nested": {"would_have_outcome": "allow"},
        },
        undo={"blocked_execution": True},
    )

    payloads = [
        snapshot.to_dict(),
        action_snapshot_to_surface(snapshot).to_dict(),
        action_snapshot_to_context(snapshot).to_dict(),
    ]

    for payload in payloads:
        assert not AUTHORITY_FIELDS.intersection(payload)
        assert not _contains_key_recursive(payload, AUTHORITY_FIELDS)


def test_action_snapshot_module_does_not_import_runtime_api_db_or_report_services():
    source = inspect.getsource(snapshot_module)

    for marker in RUNTIME_IMPORT_MARKERS:
        assert marker not in source

    assert "PolicyGateEvaluation" not in vars(snapshot_module)
    assert "PolicyGateDryRunEvaluation" not in vars(snapshot_module)
    assert "create_policy_gate_dry_run_observation" not in vars(snapshot_module)
