import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost, formatApiError } from "../api/client";
import { JsonDetails, PathValue, metadataText } from "../components/AuditDisplay";
import type {
  ActionResponse,
  JsonObject,
  LocalProofScanSummary,
  LocalProofSuggestActionsSummary,
} from "../types";

type ActionOperation = "approve" | "execute" | "undo" | "reject";

const ACTION_LABELS: Record<ActionOperation, string> = {
  approve: "Approve",
  execute: "Execute",
  undo: "Undo",
  reject: "Reject",
};

export function LocalProof() {
  const [folderPath, setFolderPath] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [maxFiles, setMaxFiles] = useState(500);
  const [caseId, setCaseId] = useState("");
  const [targetRoot, setTargetRoot] = useState("");
  const [scanResult, setScanResult] = useState<LocalProofScanSummary | null>(null);
  const [suggestResult, setSuggestResult] = useState<LocalProofSuggestActionsSummary | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [gateDecisionReady, setGateDecisionReady] = useState<Set<string>>(
    () => new Set(),
  );

  function scanFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setScanLoading(true);
    apiPost<LocalProofScanSummary>("/localproof/scan", {
      folder_path: folderPath,
      recursive,
      max_files: maxFiles,
    })
      .then((response) => {
        setScanResult(response);
        setSuggestResult(null);
        setCaseId(response.case_id);
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setScanLoading(false));
  }

  function suggestActions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuggestLoading(true);
    apiPost<LocalProofSuggestActionsSummary>("/localproof/suggest-actions", {
      case_id: caseId,
      target_root: targetRoot,
    })
      .then((response) => {
        setSuggestResult(response);
        setCaseId(response.case_id);
        setGateDecisionReady(new Set());
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setSuggestLoading(false));
  }

  function refreshActions(currentCaseId: string) {
    return apiGet<ActionResponse[]>(`/cases/${currentCaseId}/actions`).then((actions) => {
      setSuggestResult((current) => {
        if (!current) return current;
        return { ...current, actions };
      });
      setError(null);
    });
  }

  function runAction(action: ActionResponse, operation: ActionOperation) {
    const actionKey = `${action.id}:${operation}`;
    setBusyAction(actionKey);
    apiPost<ActionResponse>(`/actions/${action.id}/${operation}`)
      .then(() =>
        refreshActions(action.case_id).then(() => {
          if (operation === "execute" || operation === "reject") {
            setGateDecisionReady((current) => {
              if (!current.has(action.id)) return current;
              const next = new Set(current);
              next.delete(action.id);
              return next;
            });
          }
        }),
      )
      .catch((requestError: unknown) => setError(formatApiError(requestError)))
      .finally(() => setBusyAction(null));
  }

  const actions = useMemo(
    () => sortActionsForReview(suggestResult?.actions ?? []),
    [suggestResult?.actions],
  );

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">LocalProof</p>
          <h1>File evidence workflow</h1>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}

      <div className="two-column">
        <form className="panel form-grid" onSubmit={scanFolder}>
          <h2>Scan folder</h2>
          <label>
            Folder path
            <input
              value={folderPath}
              placeholder="D:\\Inbox or C:\\Users\\me\\Documents"
              onChange={(event) => setFolderPath(event.target.value)}
            />
          </label>
          <label>
            Max files
            <input
              type="number"
              min={1}
              value={maxFiles}
              onChange={(event) => setMaxFiles(Number(event.target.value))}
            />
          </label>
          <label className="inline-field">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(event) => setRecursive(event.target.checked)}
            />
            Recursive
          </label>
          <button type="submit" disabled={!folderPath.trim() || scanLoading}>
            {scanLoading ? "Scanning..." : "Scan"}
          </button>
        </form>

        <form className="panel form-grid" onSubmit={suggestActions}>
          <h2>Suggest actions</h2>
          <label>
            Case ID
            <input value={caseId} onChange={(event) => setCaseId(event.target.value)} />
          </label>
          <label>
            Target root
            <input
              value={targetRoot}
              placeholder="D:\\ProofFlowSorted"
              onChange={(event) => setTargetRoot(event.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={!caseId.trim() || !targetRoot.trim() || suggestLoading}
          >
            {suggestLoading ? "Suggesting..." : "Suggest actions"}
          </button>
        </form>
      </div>

      <section className="panel">
        <div className="section-heading">
          <h2>Scan summary</h2>
          {activeCaseId(scanResult, suggestResult, caseId) && (
            <Link className="secondary-action" to={`/cases/${activeCaseId(scanResult, suggestResult, caseId)}`}>
              Open Case
            </Link>
          )}
        </div>
        {scanResult ? (
          <>
            <dl className="detail-list">
              <div>
                <dt>Case</dt>
                <dd className="mono-cell">
                  <Link to={`/cases/${scanResult.case_id}`}>{scanResult.case_id}</Link>
                </dd>
              </div>
              <div>
                <dt>Files seen</dt>
                <dd>{scanResult.files_seen}</dd>
              </div>
              <div>
                <dt>Artifacts created</dt>
                <dd>{scanResult.artifacts_created}</dd>
              </div>
              <div>
                <dt>Artifacts updated</dt>
                <dd>{scanResult.artifacts_updated}</dd>
              </div>
              <div>
                <dt>Text chunks</dt>
                <dd>{scanResult.text_chunks_created}</dd>
              </div>
              <div>
                <dt>Skipped</dt>
                <dd>{scanResult.skipped}</dd>
              </div>
            </dl>
            <SkippedItemsTable items={scanResult.skipped_items} emptyText="No skipped scan items." />
          </>
        ) : (
          <p className="muted">No LocalProof scan yet.</p>
        )}
      </section>

      <section className="panel">
        <h2>Suggestion summary</h2>
        {suggestResult ? (
          <>
            <dl className="detail-list">
              <div>
                <dt>Case</dt>
                <dd className="mono-cell">
                  <Link to={`/cases/${suggestResult.case_id}`}>{suggestResult.case_id}</Link>
                </dd>
              </div>
              <div>
                <dt>Target root</dt>
                <dd>
                  <PathValue value={suggestResult.target_root} />
                </dd>
              </div>
              <div>
                <dt>Actions created</dt>
                <dd>{suggestResult.actions_created}</dd>
              </div>
              <div>
                <dt>Skipped</dt>
                <dd>{suggestResult.skipped}</dd>
              </div>
            </dl>
            <SkippedItemsTable
              items={suggestResult.skipped_items}
              emptyText="No skipped suggestion items."
            />
          </>
        ) : (
          <p className="muted">No organization suggestions yet.</p>
        )}
      </section>

      <section className="panel">
        <h2>Suggested actions</h2>
        {actions.length === 0 ? (
          <p className="muted">No suggested actions to review.</p>
        ) : (
          <ul className="packet-list">
            {actions.map((action) => (
              <li key={action.id} className="packet-item" data-action-id={action.id}>
                <div className="section-heading compact">
                  <div>
                    <strong>{action.title}</strong>
                    <div className="muted">
                      {action.kind} / {action.reason}
                    </div>
                  </div>
                  <span className={`status-pill${action.status === "pending_decision" ? " warn" : ""}`}>{action.status}</span>
                </div>
                <ActionStatusSummary
                  action={action}
                  gateDecisionReady={gateDecisionReady.has(action.id)}
                />
                <div className="path-preview-grid">
                  <ActionPathPreview action={action} />
                </div>
                <div className="details-grid">
                  <JsonDetails label="Preview" value={action.preview} />
                  <JsonDetails label="Result" value={action.result} />
                  <JsonDetails label="Undo" value={action.undo} />
                  <JsonDetails label="Metadata" value={action.metadata} />
                </div>
                <ActionDependencyMetadata metadata={action.metadata} />
                {action.status === "pending_decision" && (
                  <PolicyGateBanner
                    action={action}
                    decisionReady={gateDecisionReady.has(action.id)}
                    onDecisionCreated={() =>
                      refreshActions(action.case_id).then(() =>
                        setGateDecisionReady((current) => {
                          const next = new Set(current);
                          next.add(action.id);
                          return next;
                        }),
                      )
                    }
                    busy={busyAction !== null}
                  />
                )}
                <div className="action-buttons">
                  {(["approve", "execute", "undo", "reject"] as ActionOperation[]).map((operation) => (
                    <button
                      key={operation}
                      type="button"
                      disabled={
                        busyAction !== null ||
                        !canRunAction(
                          action,
                          operation,
                          gateDecisionReady.has(action.id),
                        ) ||
                        busyAction === `${action.id}:${operation}`
                      }
                      aria-label={`${ACTION_LABELS[operation]} ${action.title}`}
                      onClick={() => runAction(action, operation)}
                    >
                      {busyAction === `${action.id}:${operation}`
                        ? "Working..."
                        : ACTION_LABELS[operation]}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function activeCaseId(
  scanResult: LocalProofScanSummary | null,
  suggestResult: LocalProofSuggestActionsSummary | null,
  caseId: string,
): string {
  return suggestResult?.case_id ?? scanResult?.case_id ?? caseId.trim();
}

function SkippedItemsTable({
  items,
  emptyText,
}: {
  items: Array<{ path: string | null; reason: string; indexed?: boolean }>;
  emptyText: string;
}) {
  if (items.length === 0) {
    return <p className="muted">{emptyText}</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Path</th>
            <th>Reason</th>
            <th>Indexed</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.path ?? "unknown"}-${index}`}>
              <td>
                <PathValue label="Path" value={item.path} />
              </td>
              <td>{item.reason}</td>
              <td>{item.indexed === undefined ? "not applicable" : item.indexed ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActionPathPreview({ action }: { action: ActionResponse }) {
  if (action.kind === "mkdir_dir") {
    return <PathValue label="Directory" value={previewText(action.preview, "dir_path")} />;
  }
  if (action.kind === "move_file" || action.kind === "rename_file") {
    return (
      <>
        <PathValue label="From" value={previewText(action.preview, "from_path")} />
        <PathValue label="To" value={previewText(action.preview, "to_path")} />
      </>
    );
  }
  return <PathValue label="Preview" value={previewText(action.preview, "path")} />;
}

function ActionDependencyMetadata({ metadata }: { metadata: JsonObject }) {
  const dependsOnActionId = metadataText(metadata, "depends_on_action_id");
  const dependsOnDirPath = metadataText(metadata, "depends_on_dir_path");
  if (dependsOnActionId === "not recorded" && dependsOnDirPath === "not recorded") {
    return null;
  }
  return (
    <div className="path-preview-grid">
      <PathValue label="Depends on action" value={dependsOnActionId} />
      <PathValue label="Depends on directory" value={dependsOnDirPath} />
    </div>
  );
}

function canRunAction(
  action: ActionResponse,
  operation: ActionOperation,
  gateDecisionReady = false,
): boolean {
  if (operation === "approve") return action.status === "pending" || action.status === "previewed";
  if (operation === "execute") {
    return action.status === "approved" || (action.status === "pending_decision" && gateDecisionReady);
  }
  if (operation === "undo") {
    return action.status === "executed" && action.kind !== "manual_check";
  }
  if (operation === "reject") {
    return (
      action.status === "pending" ||
      action.status === "previewed" ||
      action.status === "approved" ||
      action.status === "pending_decision"
    );
  }
  return false;
}

function previewText(preview: JsonObject, key: string): string {
  const value = preview[key];
  return typeof value === "string" && value ? value : "not recorded";
}

function PolicyGateBanner({
  action,
  decisionReady,
  onDecisionCreated,
  busy,
}: {
  action: ActionResponse;
  decisionReady: boolean;
  onDecisionCreated: () => void;
  busy: boolean;
}) {
  const [creating, setCreating] = useState(false);
  const gate = action.metadata.policy_gate as Record<string, unknown> | undefined;
  if (!gate) return null;

  const categories = Array.isArray(gate.categories) ? (gate.categories as string[]).join(", ") : "";
  const reason = typeof gate.reason === "string" ? gate.reason : "";
  const pipelineId = gate.pipeline_id as string | undefined;
  const previewHash = gate.preview_hash as string | undefined;

  function createGateDecision() {
    setCreating(true);
    apiPost<unknown>(`/cases/${action.case_id}/decisions`, {
      title: `Approve gated action: ${action.title}`,
      status: "accepted",
      rationale: reason || "Owner approves high-risk action after review.",
      result: "proceed",
      metadata: {
        decision_kind: "policy_gate_owner_decision",
        action_id: action.id,
        policy_evaluation_id: pipelineId,
        preview_hash: previewHash,
      },
    })
      .then(() => onDecisionCreated())
      .catch(() => {})
      .finally(() => setCreating(false));
  }

  return (
    <div className={`gate-banner${decisionReady ? " ready" : ""}`}>
      <strong>Policy gate - action paused</strong>
      {reason && <span>{reason}</span>}
      {categories && <span>Categories: {categories}</span>}
      <span>
        {decisionReady
          ? "Owner decision recorded. Step 2 of 2: click Execute to run this action."
          : "Step 1 of 2: record an owner decision. Step 2 will be a separate Execute click."}
      </span>
      <button
        type="button"
        onClick={createGateDecision}
        disabled={busy || creating || decisionReady}
      >
        {creating
          ? "Recording decision..."
          : decisionReady
            ? "Owner Decision Recorded"
            : "Record Owner Decision"}
      </button>
    </div>
  );
}

function ActionStatusSummary({
  action,
  gateDecisionReady,
}: {
  action: ActionResponse;
  gateDecisionReady: boolean;
}) {
  return (
    <div className="action-summary">
      <strong>{actionStatusText(action, gateDecisionReady)}</strong>
      <span>{nextActionText(action, gateDecisionReady)}</span>
    </div>
  );
}

function actionStatusText(action: ActionResponse, gateDecisionReady = false): string {
  if (action.status === "pending_decision") {
    return gateDecisionReady
      ? "Owner decision recorded; execute is now available."
      : "Owner decision required before execution.";
  }
  if (action.status === "pending" || action.status === "previewed") return "Preview is ready for approval.";
  if (action.status === "approved") return "Approved and ready to execute.";
  if (action.status === "executed") return "Executed with undo metadata recorded.";
  if (action.status === "undone") return "Undo completed.";
  if (action.status === "rejected") return "Rejected.";
  return "Action state recorded.";
}

function nextActionText(action: ActionResponse, gateDecisionReady = false): string {
  if (action.status === "pending_decision" && !gateDecisionReady) {
    return "Next: Record Owner Decision or Reject.";
  }
  const available = (["approve", "execute", "undo", "reject"] as ActionOperation[])
    .filter((operation) => canRunAction(action, operation, gateDecisionReady))
    .map((operation) => ACTION_LABELS[operation]);
  if (available.length === 0) return "No further action is currently available.";
  return `Next: ${available.join(" or ")}.`;
}

function sortActionsForReview(actions: ActionResponse[]): ActionResponse[] {
  return [...actions].sort((left, right) => {
    return left.created_at.localeCompare(right.created_at) || left.title.localeCompare(right.title);
  });
}
