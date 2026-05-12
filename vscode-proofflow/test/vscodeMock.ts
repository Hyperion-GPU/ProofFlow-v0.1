type QuickPickItem = { label: string; [key: string]: unknown };
type WorkspaceFolder = { uri: { fsPath: string }; name?: string; index?: number };
type InfoSelection = string | undefined;

let pickedItem: QuickPickItem | undefined;
let pickedWorkspaceFolder: WorkspaceFolder | undefined;
let workspaceFolderList: WorkspaceFolder[] | undefined;
let infoSelection: InfoSelection;

export const infoMessages: string[] = [];
export const infoMessageItems: string[][] = [];
export const errorMessages: string[] = [];
export const executedCommands: string[] = [];

export function uri(fsPath: string): { fsPath: string } {
  return { fsPath };
}

export function workspaceFolder(path: string): WorkspaceFolder {
  return {
    uri: uri(path),
    name: path.split(/[\\/]/).filter(Boolean).pop() || path,
    index: 0,
  };
}

export function setQuickPickResult(item: QuickPickItem | undefined): void {
  pickedItem = item;
}

export function setWorkspaceFolders(
  folders: WorkspaceFolder[] | undefined
): void {
  workspaceFolderList = folders;
}

export function setWorkspaceFolderPickResult(
  folder: WorkspaceFolder | undefined
): void {
  pickedWorkspaceFolder = folder;
}

export function setInformationMessageSelection(
  selection: InfoSelection
): void {
  infoSelection = selection;
}

export function resetVscodeMock(): void {
  pickedItem = undefined;
  pickedWorkspaceFolder = undefined;
  workspaceFolderList = undefined;
  infoSelection = undefined;
  infoMessages.length = 0;
  infoMessageItems.length = 0;
  errorMessages.length = 0;
  executedCommands.length = 0;
}

export const ProgressLocation = {
  Notification: 15,
};

export const workspace = {
  get workspaceFolders(): WorkspaceFolder[] | undefined {
    return workspaceFolderList;
  },
  async showWorkspaceFolderPick(): Promise<WorkspaceFolder | undefined> {
    return pickedWorkspaceFolder;
  },
  getWorkspaceFolder(selectedUri: { fsPath: string }): WorkspaceFolder | undefined {
    const folders = workspaceFolderList || [];
    let bestMatch: WorkspaceFolder | undefined;
    for (const folder of folders) {
      const root = normalizePath(folder.uri.fsPath);
      const selected = normalizePath(selectedUri.fsPath);
      if (selected === root || selected.startsWith(`${root}/`)) {
        if (
          !bestMatch ||
          root.length > normalizePath(bestMatch.uri.fsPath).length
        ) {
          bestMatch = folder;
        }
      }
    }
    return bestMatch;
  },
  getConfiguration(): { get<T>(_key: string, fallback: T): T } {
    return {
      get<T>(_key: string, fallback: T): T {
        return fallback;
      },
    };
  },
  onDidChangeConfiguration(): { dispose(): void } {
    return { dispose() {} };
  },
};

export const window = {
  showInformationMessage(message: string, ...items: string[]): Thenable<string | undefined> {
    infoMessages.push(message);
    infoMessageItems.push(items);
    return Promise.resolve(infoSelection);
  },
  showErrorMessage(message: string): Thenable<void> {
    errorMessages.push(message);
    return Promise.resolve();
  },
  async showQuickPick<T extends QuickPickItem>(items: T[]): Promise<T | undefined> {
    if (!pickedItem) {
      return undefined;
    }
    return items.find((item) => item.label === pickedItem?.label);
  },
  async showWorkspaceFolderPick(): Promise<WorkspaceFolder | undefined> {
    return pickedWorkspaceFolder;
  },
  async withProgress<T>(
    _options: unknown,
    task: () => Promise<T>
  ): Promise<T> {
    return task();
  },
  createStatusBarItem(): {
    text: string;
    backgroundColor: unknown;
    tooltip: string;
    command: string | undefined;
    show(): void;
    dispose(): void;
  } {
    return {
      text: "",
      backgroundColor: undefined,
      tooltip: "",
      command: undefined,
      show() {},
      dispose() {},
    };
  },
};

export const commands = {
  executeCommand(command: string): void {
    executedCommands.push(command);
  },
};

export const StatusBarAlignment = {
  Left: 1,
};

export class ThemeColor {
  constructor(readonly id: string) {}
}

export class ThemeIcon {
  constructor(readonly id: string, readonly color?: ThemeColor) {}
}

function normalizePath(value: string): string {
  return value.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}
