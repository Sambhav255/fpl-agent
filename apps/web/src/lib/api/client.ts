import type { components } from "./schema";
export type State = components["schemas"]["ManagerState"];
export type Player = components["schemas"]["Player"];
export type Pick = components["schemas"]["Pick"];
export type Settings = components["schemas"]["Settings"];
export type Run = components["schemas"]["ProjectionRun"];
export type Recommendation = components["schemas"]["Recommendation"];
export type Plan = components["schemas"]["Plan"];
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  body?: unknown,
  method = body === undefined ? "GET" : "POST",
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method,
    signal,
    headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      response.status,
      payload?.message ||
        payload?.detail?.message ||
        (typeof payload?.detail === "string"
          ? payload.detail
          : `Request failed (${response.status}). Please retry.`),
      payload?.code,
    );
  return payload as T;
}
export type Job<T> = {
  job_id: string;
  status: string;
  progress: number;
  result: T | null;
  error: unknown;
};
export async function waitForJob<T>(
  jobId: string,
  update: (job: Job<T>) => void,
  signal: AbortSignal,
): Promise<T> {
  for (;;) {
    const job = await api<Job<T>>(`/jobs/${encodeURIComponent(jobId)}`, undefined, "GET", signal);
    update(job);
    if (job.status === "succeeded" && job.result) return job.result;
    if (["failed", "cancelled"].includes(job.status))
      throw new Error(
        typeof job.error === "string"
          ? job.error
          : JSON.stringify(job.error || "Analysis did not complete."),
      );
    await new Promise<void>((resolve, reject) => {
      const onAbort = () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = setTimeout(() => {
        signal.removeEventListener("abort", onAbort);
        resolve();
      }, 800);
      signal.addEventListener("abort", onAbort, { once: true });
      if (signal.aborted) onAbort();
    });
  }
}
export function money(units: number | null | undefined) {
  return units == null ? "Unknown" : `£${(units / 10).toFixed(1)}m`;
}
export function parseMoney(value: string): number | null {
  if (!value.trim()) return null;
  if (!/^\d+(?:\.\d)?$/.test(value) || !Number.isSafeInteger(Math.round(Number(value) * 10)))
    throw new Error("Use a nonnegative price with at most one decimal place.");
  return Math.round(Number(value) * 10);
}
export function teamId(value: string): number {
  const trimmed = value.trim();
  const match = /^https:\/\/fantasy\.premierleague\.com\/entry\/(\d+)\/event\/\d+\/?$/.exec(
    trimmed,
  );
  const raw = match ? match[1] : trimmed;
  if (!/^\d+$/.test(raw) || Number(raw) < 1 || !Number.isSafeInteger(Number(raw)))
    throw new Error("Enter a positive numeric team ID or an official FPL Points page URL.");
  return Number(raw);
}
export function totals(run: Run | null, event?: number) {
  const map = new Map<number, { points: number; minutes: number; fixtures: number }>();
  for (const row of run?.projections || []) {
    if (event !== undefined && row.event !== event) continue;
    const old = map.get(row.player_id) || { points: 0, minutes: 0, fixtures: 0 };
    map.set(row.player_id, {
      points: old.points + row.expected_points,
      minutes: old.minutes + row.expected_minutes,
      fixtures: old.fixtures + 1,
    });
  }
  return map;
}
