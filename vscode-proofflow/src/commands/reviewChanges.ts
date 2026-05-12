import * as vscode from "vscode";
import { ProofFlowClient } from "../api/client";

export async function reviewChanges(
  client: ProofFlowClient,
  selectedUri?: vscode.Uri
): Promise<void> {
  const repoPath = selectedUri
    ? resolveWorkspaceRoot(selectedUri)
    : await pickWorkspaceFolderPath();
  if (!repoPath) {
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "ProofFlow: Reviewing AI changes...",
      cancellable: false,
    },
    async () => {
      try {
        const result = await client.review(repoPath);
        vscode.window.showInformationMessage(
          `ProofFlow: Review complete - ${result.risk_level} risk, ${result.claims_created} claim(s), ${result.changed_files.length} file(s)`
        );
        vscode.commands.executeCommand("proofflow.refresh");
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Unknown error";
        if (msg.includes("fetch") || msg.includes("ECONNREFUSED")) {
          vscode.window.showErrorMessage(
            "ProofFlow backend not running. Start with:\n  python -m uvicorn proofflow.main:app --port 8787"
          );
        } else {
          vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
        }
      }
    }
  );
}

function resolveWorkspaceRoot(selectedUri: vscode.Uri): string | undefined {
  const folder = vscode.workspace.getWorkspaceFolder(selectedUri);
  if (!folder) {
    vscode.window.showErrorMessage(
      "ProofFlow: Selected item is not inside a workspace folder."
    );
    return undefined;
  }
  return folder.uri.fsPath;
}

async function pickWorkspaceFolderPath(): Promise<string | undefined> {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showErrorMessage("ProofFlow: No workspace folder open.");
    return undefined;
  }

  let folder: vscode.WorkspaceFolder;
  if (folders.length === 1) {
    folder = folders[0];
  } else {
    const picked = await vscode.window.showWorkspaceFolderPick({
      placeHolder: "Select workspace to review",
    });
    if (!picked) {
      return undefined;
    }
    folder = picked;
  }

  return folder.uri.fsPath;
}
