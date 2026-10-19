import product from "../../../../../packages/contracts/product.json";

export const PRODUCT = product;

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FIELD_LABELS: Record<string, string> = {
  age_months: "Age (months)",
  sex: "Sex",
  weight_kg: "Weight (kg)",
  height_cm: "Height (cm)",
  birth_weight_kg: "Birth weight (kg)",
  maternal_bmi: "Maternal BMI",
  gestational_age_weeks: "Gestational age (weeks)",
  household_size: "Household size",
  dietary_diversity_score: "Dietary diversity score",
  meal_frequency: "Meal frequency",
};

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const lines = detail.map((item) => {
      if (!item || typeof item !== "object") return "Check the entered values and try again.";
      const row = item as { loc?: unknown[]; msg?: string };
      const loc = Array.isArray(row.loc) ? row.loc.filter((part) => part !== "body").map(String) : [];
      const field = loc.length ? FIELD_LABELS[loc[loc.length - 1]] ?? loc[loc.length - 1].replaceAll("_", " ") : "";
      const msg = row.msg ?? "This value could not be accepted.";
      return field ? `${field}: ${msg}` : msg;
    });
    return lines.filter(Boolean).join(" ");
  }
  if (detail && typeof detail === "object") {
    const row = detail as { message?: string; quality?: { blocking_errors?: { field?: string; message?: string }[] } };
    const issues = row.quality?.blocking_errors ?? [];
    const lines = issues.map((issue) => {
      const field = issue.field ? FIELD_LABELS[issue.field] ?? issue.field.replaceAll("_", " ") : "";
      return field && issue.message && !issue.message.startsWith(field) ? `${field}: ${issue.message}` : issue.message ?? field;
    });
    if (lines.length) return lines.join(" ");
    if (row.message) return row.message;
  }
  return "The visit could not be saved. Check the entered measurements and try again.";
}

const STATUS_MESSAGES: Record<number, string> = {
  401: "Your session has expired. Please sign in again.",
  403: "You do not have permission to access this information.",
  422: "Please review the highlighted visit information.",
  503: "The prediction service is currently unavailable.",
};

function clinicalMessage(status: number, detail: unknown): string {
  const specific = formatApiDetail(detail);
  const generic = STATUS_MESSAGES[status];
  if (!generic) return specific;
  if (status === 422 && specific && !specific.startsWith("The visit could not be saved")) return specific;
  if (status === 503 && typeof detail === "string" && /model|prediction|inference/i.test(detail)) return `${generic} ${detail}`;
  return generic;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(clinicalMessage(status, detail));
    this.status = status;
    this.detail = detail;
  }
}

function readCsrf() {
  if (typeof window === "undefined") return "";
  const match = document.cookie.match(/(?:^|; )cnip_csrf=([^;]*)/);
  return (match ? decodeURIComponent(match[1]) : "") || sessionStorage.getItem("cnip_csrf") || "";
}

export function persistCsrf(token?: string) {
  if (token && typeof sessionStorage !== "undefined") sessionStorage.setItem("cnip_csrf", token);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = readCsrf();
  if (csrf) headers.set("X-CSRF-Token", csrf);
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && !path.startsWith("/auth/")) {
    if (!path.startsWith("/auth/refresh")) {
      try {
        const refreshed = await fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" });
        if (refreshed.ok) {
          const body = await refreshed.json();
          persistCsrf(body.csrf_token);
          return api<T>(path, init);
        }
      } catch {
        /* fall through */
      }
    }
    if (typeof window !== "undefined") window.location.href = "/login";
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? body.message ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
