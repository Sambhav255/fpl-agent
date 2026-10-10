import {
  api,
  ApiError,
  teamId,
  waitForJob,
  type Plan,
  type Recommendation,
  type Run,
  type State,
} from "../lib/api/client";
import type { PlannerSettings } from "./planner/types";
import { transferSearchAllowed } from "./planner/logic";
import type { Readiness } from "./use-workspace";

type Saved = {
  team_id: number;
  plan_id: string;
  plan: Plan;
  recommendation_id: string;
  input_fingerprint: string;
  saved_at: string;
  stale_reasons?: string[];
};
type Task = (name: string, action: (signal: AbortSignal) => Promise<void>) => Promise<void>;

export function bindTask(
  controller: { current: AbortController | null },
  jobId: { current: string | null },
  setBusy: (value: string) => void,
  setProgress: (value: number) => void,
  setError: (value: string) => void,
  setNotice: (value: string) => void,
  setActiveJob: (value: string | null) => void,
): Task {
  return async (name, action) => {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(name);
    setProgress(0);
    setError("");
    setNotice("");
    try {
      await action(abort.signal);
    } catch (taskError) {
      if (!abort.signal.aborted) {
        setError(taskError instanceof Error ? taskError.message : "Request failed.");
        if (taskError instanceof ApiError && taskError.status === 409)
          setNotice(
            "Inputs changed. Reload current state, then review and save your corrections again.",
          );
      }
    } finally {
      if (controller.current === abort) {
        jobId.current = null;
        setActiveJob(null);
        setBusy("");
      }
    }
  };
}

export function analysisMode(
  state: State,
  readiness: Readiness | null,
  requested?: "transfers" | "lineup",
) {
  const allowed =
    transferSearchAllowed({
      bank: state.bank_units,
      free: state.free_transfers_at_event_start,
      made: state.transfers_made_this_event,
      hits: state.confirmed_hit_points,
      picks: state.picks,
    }) && readiness?.transfers_ready === true;
  return requested === "lineup" || !allowed ? "lineup" : "transfers";
}

export async function postAnalysis(input: {
  state: State;
  settings: PlannerSettings;
  mode: "transfers" | "lineup";
  signal: AbortSignal;
  jobId: { current: string | null };
  setActiveJob: (value: string | null) => void;
  setProgress: (value: number) => void;
  setBusy: (value: string) => void;
  setRun: (run: Run) => void;
  setRecommendation: (value: Recommendation) => void;
}) {
  const queued = await api<{ job_id: string }>(
    "/projections/runs",
    { team_id: input.state.team_id, horizon_events: input.settings.horizon_events },
    "POST",
    input.signal,
  );
  input.jobId.current = queued.job_id;
  input.setActiveJob(queued.job_id);
  const forecast = await waitForJob<Run>(
    queued.job_id,
    (job) => input.setProgress(job.progress),
    input.signal,
  );
  if (input.signal.aborted) return;
  input.setRun(forecast);
  const key = `touchline.artifacts.${input.state.team_id}.${input.state.state_version}`;
  sessionStorage.setItem(
    key,
    JSON.stringify({ run: forecast.projection_run_id, settings: input.settings }),
  );
  input.setBusy("Finding independently validated plans");
  const analysis = await api<{ job_id: string }>(
    "/recommendations",
    {
      team_id: input.state.team_id,
      expected_state_version: input.state.state_version,
      projection_run_id: forecast.projection_run_id,
      settings: input.settings,
      analysis_mode: input.mode,
    },
    "POST",
    input.signal,
  );
  input.jobId.current = analysis.job_id;
  input.setActiveJob(analysis.job_id);
  const result = await waitForJob<Recommendation>(
    analysis.job_id,
    (job) => input.setProgress(job.progress),
    input.signal,
  );
  if (input.signal.aborted) return;
  input.setRecommendation(result);
  sessionStorage.setItem(
    key,
    JSON.stringify({
      run: forecast.projection_run_id,
      recommendation: result.recommendation_id,
      settings: input.settings,
    }),
  );
}

export async function postPlan(
  recommendationId: string,
  plan: Plan,
  teamIdValue: number | undefined,
  signal: AbortSignal,
) {
  await api(
    "/plans",
    { recommendation_id: recommendationId, plan_id: plan.plan_id },
    "POST",
    signal,
  );
  const plans = await api<Saved[]>("/plans", undefined, "GET", signal);
  return plans.filter((item) => item.team_id === teamIdValue);
}

export async function patchManager(
  team: number,
  expectedVersion: number,
  next: State,
  signal: AbortSignal,
) {
  return api<State>(
    `/teams/${team}/state`,
    { expected_version: expectedVersion, state: next },
    "PATCH",
    signal,
  );
}

export function importBody(demo: boolean, value: string) {
  return demo ? null : { team_id: teamId(value) };
}
