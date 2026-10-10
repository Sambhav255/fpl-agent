"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  totals,
  type Recommendation,
  type Run,
  type State,
} from "../lib/api/client";
import type { components } from "../lib/api/schema";
import { preferredTeamId } from "../lib/profile";
import { transferSearchAllowed } from "./planner/logic";
import { defaultSettings, type PlannerSettings } from "./planner/types";

type Saved = components["schemas"]["SavedPlan"];
type Catalog = components["schemas"]["PlayersResponse"];
export type Readiness = {
  transfers_ready: boolean;
  lineup_ready: boolean;
  missing_fields: string[];
  errors: string[];
};

export function useWorkspace() {
  const [state, setState] = useState<State | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [status, setStatus] = useState<Record<string, unknown>>({});
  const [saved, setSaved] = useState<Saved[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [settings, setSettings] = useState<PlannerSettings>(defaultSettings);
  const [importValue, setImportValue] = useState("");
  const [busy, setBusy] = useState("Loading workspace");
  const [progress, setProgress] = useState(0);
  const [activeJob, setActiveJob] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dirty, setDirty] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const jobId = useRef<string | null>(null);
  const playerMap = new Map((catalog?.players || []).map((player) => [player.player_id, player]));
  const points = totals(run, state?.next_event);
  const stale = Boolean(state && catalog && state.snapshot_id !== catalog.snapshot_id);
  const transfersAllowed =
    Boolean(state) &&
    transferSearchAllowed({
      bank: state?.bank_units,
      free: state?.free_transfers_at_event_start,
      made: state?.transfers_made_this_event,
      hits: state?.confirmed_hit_points,
      picks: state?.picks || [],
    }) &&
    readiness?.transfers_ready === true &&
    !dirty &&
    !stale;

  const loadWorkspace = useCallback(async (manager: State, signal: AbortSignal) => {
    const [players, freshness, plans, readyState] = await Promise.all([
      api<Catalog>(`/players?data_mode=${manager.data_mode}`, undefined, "GET", signal),
      api<Record<string, unknown>>(
        `/status?data_mode=${manager.data_mode}`,
        undefined,
        "GET",
        signal,
      ),
      api<Saved[]>("/plans", undefined, "GET", signal),
      api<Readiness>(`/teams/${manager.team_id}/readiness`, undefined, "GET", signal).catch(
        (loadError: unknown) => {
          if (signal.aborted) throw loadError;
          if (loadError instanceof ApiError && loadError.status === 409)
            return {
              transfers_ready: false,
              lineup_ready: false,
              missing_fields: [
                "Manager snapshot is stale. Review current prices and save corrections.",
              ],
              errors: [] as string[],
            };
          return {
            transfers_ready: false,
            lineup_ready: false,
            missing_fields: [
              "Readiness could not be verified. Reload current state before analysis.",
            ],
            errors: [] as string[],
          };
        },
      ),
    ]);
    if (signal.aborted) return;
    setReadiness(readyState);
    setCatalog(players);
    setStatus(freshness);
    setSaved(plans.filter((plan) => plan.team_id === manager.team_id));
    setState(manager);
    setDirty(false);
    localStorage.setItem("touchline.team", String(manager.team_id));
    const artifactKey = `touchline.artifacts.${manager.team_id}.${manager.state_version}`;
    const stored = sessionStorage.getItem(artifactKey);
    if (!stored) return;
    try {
      const references = JSON.parse(stored) as {
        run: string;
        recommendation?: string;
        settings?: PlannerSettings;
      };
      const forecast = await api<Run>(
        `/projections/runs/${encodeURIComponent(references.run)}`,
        undefined,
        "GET",
        signal,
      );
      if (signal.aborted || forecast.snapshot_id !== players.snapshot_id) return;
      setRun(forecast);
      setSettings({
        ...defaultSettings,
        ...(references.settings || {}),
        horizon_events: forecast.horizon_events,
      });
      if (!references.recommendation) return;
      const result = await api<Recommendation>(
        `/recommendations/${encodeURIComponent(references.recommendation)}`,
        undefined,
        "GET",
        signal,
      );
      if (!signal.aborted) setRecommendation(result);
    } catch {
      sessionStorage.removeItem(artifactKey);
    }
  }, []);

  useEffect(() => {
    const abort = new AbortController();
    controller.current = abort;
    async function start() {
      try {
        const id = preferredTeamId();
        if (id !== null && /^\d+$/.test(id))
          await loadWorkspace(
            await api<State>(`/teams/${id}/state`, undefined, "GET", abort.signal),
            abort.signal,
          );
      } catch (loadError) {
        if (!abort.signal.aborted)
          setError(loadError instanceof Error ? loadError.message : "Workspace could not load.");
      } finally {
        if (!abort.signal.aborted) setBusy("");
      }
    }
    void start();
    return () => abort.abort();
  }, [loadWorkspace]);

  const cancelJob = () => {
    controller.current?.abort();
    if (jobId.current) void api(`/jobs/${jobId.current}/cancel`, {}).catch(() => {});
    jobId.current = null;
    setActiveJob(null);
    setBusy("");
    setNotice("Stopped waiting for analysis. You can retry.");
  };
  return {
    state,
    catalog,
    status,
    saved,
    setSaved,
    run,
    recommendation,
    settings,
    setSettings,
    importValue,
    setImportValue,
    busy,
    setBusy,
    progress,
    setProgress,
    activeJob,
    setActiveJob,
    readiness,
    error,
    setError,
    notice,
    setNotice,
    dirty,
    stale,
    transfersAllowed,
    playerMap,
    points,
    controller,
    jobId,
    loadWorkspace,
    setRun,
    setRecommendation,
    setState,
    cancelJob,
  };
}
