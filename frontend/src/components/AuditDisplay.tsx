import type { JsonObject } from "../types";

export function PathValue({
  label,
  value,
}: {
  label?: string;
  value: string | null | undefined;
}) {
  const text = value || "not recorded";
  return (
    <div className="path-preview">
      {label && <strong>{label}</strong>}
      <details className="path-details">
        <summary title={text}>{compactPath(text)}</summary>
        <span>{text}</span>
      </details>
    </div>
  );
}

export function JsonDetails({
  label,
  value,
  defaultOpen = false,
}: {
  label: string;
  value: unknown;
  defaultOpen?: boolean;
}) {
  const formatted = formatJson(value);
  const empty = formatted === "not recorded";
  return (
    <details className="audit-details" open={defaultOpen && !empty}>
      <summary>
        <strong>{label}</strong>
        <span>{empty ? "not recorded" : jsonSummary(value)}</span>
      </summary>
      {!empty && <pre>{formatted}</pre>}
    </details>
  );
}

export function metadataText(metadata: JsonObject | undefined, key: string): string {
  if (!metadata) return "not recorded";
  const value = metadata[key];
  if (value === null || value === undefined) return "not recorded";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function formatJson(value: unknown): string {
  if (value === null || value === undefined || isEmptyObject(value)) {
    return "not recorded";
  }
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

export function compactPath(value: string): string {
  if (!value || value === "not recorded") return value || "not recorded";
  const normalized = value.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length <= 3) return value;
  const drive = /^[A-Za-z]:$/.test(parts[0]) ? `${parts[0]}/` : "";
  const tail = parts.slice(-2).join("/");
  return `${drive}.../${tail}`;
}

function jsonSummary(value: unknown): string {
  if (value === null || value === undefined || isEmptyObject(value)) {
    return "not recorded";
  }
  if (Array.isArray(value)) return `${value.length} items`;
  if (typeof value === "object") {
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) return "not recorded";
    return keys.slice(0, 3).join(", ") + (keys.length > 3 ? ` +${keys.length - 3}` : "");
  }
  return String(value);
}

function isEmptyObject(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.keys(value as Record<string, unknown>).length === 0
  );
}
