type QuickPickItem = { label: string; [key: string]: unknown };

let pickedItem: QuickPickItem | undefined;

export const infoMessages: string[] = [];
export const errorMessages: string[] = [];
export const executedCommands: string[] = [];

export function setQuickPickResult(item: QuickPickItem | undefined): void {
  pickedItem = item;
}

export function resetVscodeMock(): void {
  pickedItem = undefined;
  infoMessages.length = 0;
  errorMessages.length = 0;
  executedCommands.length = 0;
}

export const window = {
  showInformationMessage(message: string): void {
    infoMessages.push(message);
  },
  showErrorMessage(message: string): void {
    errorMessages.push(message);
  },
  async showQuickPick<T extends QuickPickItem>(items: T[]): Promise<T | undefined> {
    if (!pickedItem) {
      return undefined;
    }
    return items.find((item) => item.label === pickedItem?.label);
  },
};

export const commands = {
  executeCommand(command: string): void {
    executedCommands.push(command);
  },
};
