import axios from "axios";

function validationMessages(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item === "string") return [item];
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const message = typeof record.msg === "string" ? record.msg : typeof record.message === "string" ? record.message : null;
    const parts = Array.isArray(record.loc) ? record.loc.map(String) : [];
    const location = (parts[0] === "body" ? parts.slice(1) : parts).join(".");
    return message ? [`${location ? `${location}：` : ""}${message}`] : [];
  });
}

export function apiErrorMessage(error: unknown, fallback = "操作没有完成。"): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    const detail = data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    const detailMessages = validationMessages(detail);
    if (detailMessages.length) return detailMessages.join("\n");
    const errorMessages = validationMessages(data?.errors);
    if (errorMessages.length) return errorMessages.join("\n");
    if (typeof data?.message === "string" && data.message.trim()) return data.message;
    return fallback;
  }
  return error instanceof Error && error.message ? error.message : fallback;
}
