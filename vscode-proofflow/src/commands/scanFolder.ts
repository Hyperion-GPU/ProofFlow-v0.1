import * as vscode from "vscode";
import { ProofFlowClient } from "../api/client";

export async function scanFolder(
  client: ProofFlowClient,
  selectedUri?: vscode.Uri
): Promise<void> {
  const folderPath = selectedUri?.fsPath ?? (await pickWorkspaceFolderPath());
  if (!folderPath) {
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "ProofFlow: Scanning folder...",
      cancellable: false,
    },
    async () => {
      try {
        const result = await client.scan(folderPath);
        vscode.window.showInformationMessage(
          `ProofFlow: Scan complete - ${result.files_seen} file(s), ${result.artifacts_created} artifact(s)`
        );
        vscode.commands.executeCommand("proofflow.refresh");
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Unknown error";
        vscode.window.showErrorMessage(`ProofFlow: ${msg}`);
      }
    }
  );
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
      placeHolder: "Select folder to scan",
    });
    if (!picked) {
      return undefined;
    }
    folder = picked;
  }

  return folder.uri.fsPath;
}
