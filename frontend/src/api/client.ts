import type {
  BackupCreateRequest,
  BackupCreateResponse,
  BackupDetailResponse,
  BackupListResponse,
  BackupPreviewRequest,
  BackupPreviewResponse,
  BackupVerifyResponse,
  RestorePreviewRequest,
  RestorePreviewResponse,
  RestoreToNewLocationRequest,
  RestoreToNewLocationResponse,
} from "../types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8787";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API request failed with ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestBody = object | unknown[] | string | number | boolean | null;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  const text = await response.text();

  if (!response.ok) {
    const data = parseErrorBody(text);
    throw new ApiError(response.status, errorDetail(data, defaultErrorMessage(response)));
  }

  const data = parseJsonSuccess(text, response.status);
  return data as T;
}

function parseJsonSuccess(text: string, status: number): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    throw new ApiError(status, "Malformed API response: expected JSON");
  }
}

function parseErrorBody(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function errorDetail(data: unknown, fallback: string): unknown {
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    return record.detail ?? record.message ?? record.error ?? data;
  }
  return data ?? fallback;
}

function defaultErrorMessage(response: Response): string {
  return response.statusText
    ? `${response.status} ${response.statusText}`
    : `API request failed with ${response.status}`;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: RequestBody): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(body ?? {}),
  });
}

export function apiPatch<T>(path: string, body: RequestBody): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function backupPreview(
  body: BackupPreviewRequest,
): Promise<BackupPreviewResponse> {
  return apiPost<BackupPreviewResponse>("/backups/preview", body);
}

export function createBackup(
  body: BackupCreateRequest,
): Promise<BackupCreateResponse> {
  return apiPost<BackupCreateResponse>("/backups", body);
}

export function listBackups(): Promise<BackupListResponse> {
  return apiGet<BackupListResponse>("/backups");
}

export function getBackupDetail(backupId: string): Promise<BackupDetailResponse> {
  return apiGet<BackupDetailResponse>(`/backups/${encodeURIComponent(backupId)}`);
}

export function verifyBackup(backupId: string): Promise<BackupVerifyResponse> {
  return apiPost<BackupVerifyResponse>(
    `/backups/${encodeURIComponent(backupId)}/verify`,
  );
}

export function restorePreview(
  body: RestorePreviewRequest,
): Promise<RestorePreviewResponse> {
  return apiPost<RestorePreviewResponse>("/restore/preview", body);
}

export function restoreToNewLocation(
  body: RestoreToNewLocationRequest,
): Promise<RestoreToNewLocationResponse> {
  return apiPost<RestoreToNewLocationResponse>("/restore/to-new-location", body);
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") {
      return error.detail;
    }
    return JSON.stringify(error.detail);
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}
