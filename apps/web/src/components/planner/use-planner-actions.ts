"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Plan, type State } from "../../lib/api/client";
import { analysisMode, bindTask, patchManager, postAnalysis, postPlan } from "../workspace-actions";
import {
  applyAcceptedPrices,
  countFromSettings,
  parseSuggestions,
  remainingFreeTransfers,
  transferBlockReason,
  transferSettings,
  withSellMarket,
  type PriceDecision,
} from "./logic";
import { type PlannerSettings, type PriceSuggestion } from "./types";
import type { useWorkspace } from "../use-workspace";

type Workspace = ReturnType<typeof useWorkspace>;

export function usePlannerActions(ws: Workspace) {
  const [pitchPlan, setPitchPlan] = useState<Plan | null>(null);
  const [suggestions, setSuggestions] = useState<PriceSuggestion[]>([]);
  const [suggestionNote, setSuggestionNote] = useState("");
  const state = ws.state;
  const free = state?.free_transfers_at_event_start ?? null;
  const made = state?.transfers_made_this_event ?? null;
  const allowHit = ws.settings.max_additional_hit_points >= 4;
  const remaining = remainingFreeTransfers(free, made);
  const count = countFromSettings(ws.settings.max_transfers_this_event, remaining, allowHit);
  const resolved: PlannerSettings = {
    ...ws.settings,
    ...transferSettings({ count: count ?? 0, allowHit, free, made }),
  };
  const blockReason = state
    ? transferBlockReason({
        bank: state.bank_units,
        free,
        made,
        hits: state.confirmed_hit_points,
        picks: state.picks,
      })
    : "Load a team before transfer analysis.";
  const transfersAllowed = ws.transfersAllowed && blockReason == null;

  useEffect(() => {
    if (!state) return;
    const abort = new AbortController();
    api<unknown>(
      `/teams/${state.team_id}/selling-price-suggestions`,
      undefined,
      "GET",
      abort.signal,
    )
      .then((payload) => {
        if (!abort.signal.aborted) setSuggestions(parseSuggestions(payload));
      })
      .catch((loadError: unknown) => {
        if (abort.signal.aborted) return;
        setSuggestions([]);
        if (!(loadError instanceof ApiError) || ![404, 405, 501].includes(loadError.status))
          setSuggestionNote(
            "Estimated prices are unavailable. Type a confirmed price, or leave the row blank.",
          );
      });
    return () => abort.abort();
  }, [state]);

  const changeSettings = (patch: Partial<PlannerSettings>) => {
    ws.setSettings((current) => ({ ...current, ...patch }));
    ws.setRecommendation(null);
    setPitchPlan(null);
    if (state)
      sessionStorage.removeItem(`touchline.artifacts.${state.team_id}.${state.state_version}`);
  };
  const task = bindTask(
    ws.controller,
    ws.jobId,
    ws.setBusy,
    ws.setProgress,
    ws.setError,
    ws.setNotice,
    ws.setActiveJob,
  );
  const analyse = (mode: "transfers" | "lineup", patch?: Partial<PlannerSettings>) => {
    if (!state || ws.dirty || ws.stale) return;
    const next = { ...resolved, chip_policy: "none" as const, ...patch };
    void task("Generating baseline forecasts", async (signal) => {
      ws.setSettings(next);
      await postAnalysis({
        state,
        settings: next,
        mode: analysisMode(state, ws.readiness, mode),
        signal,
        jobId: ws.jobId,
        setActiveJob: ws.setActiveJob,
        setProgress: ws.setProgress,
        setBusy: ws.setBusy,
        setRun: ws.setRun,
        setRecommendation: (value) => {
          ws.setRecommendation(value);
          setPitchPlan(null);
        },
      });
      if (!signal.aborted) ws.setNotice("Analysis ready. Review assumptions before saving a plan.");
    });
  };
  const acceptPrices = (decisions: PriceDecision[]) => {
    if (!state || !ws.catalog) return;
    const picks = withSellMarket(
      applyAcceptedPrices(state.picks, decisions),
      (id) => ws.playerMap.get(id)?.market_price_units ?? null,
    );
    const next: State = { ...state, snapshot_id: ws.catalog.snapshot_id, picks };
    void task("Saving selling prices", async (signal) => {
      const updated = await patchManager(state.team_id, state.state_version, next, signal);
      await ws.loadWorkspace(updated, signal);
      if (signal.aborted) return;
      ws.setRun(null);
      ws.setRecommendation(null);
      setPitchPlan(null);
      ws.setNotice(`Selling prices saved · version ${updated.state_version}`);
    });
  };
  const savePlan = (plan: Plan) =>
    void task("Saving plan", async (signal) => {
      if (!ws.recommendation || !state) return;
      const next = await postPlan(ws.recommendation.recommendation_id, plan, state.team_id, signal);
      if (!signal.aborted) {
        ws.setSaved(next);
        ws.setNotice("Plan saved. Actions must be completed manually on FPL.");
      }
    });
  return {
    pitchPlan,
    setPitchPlan,
    suggestions,
    suggestionNote,
    free,
    made,
    allowHit,
    count,
    resolved,
    blockReason,
    transfersAllowed,
    changeSettings,
    analyse,
    acceptPrices,
    savePlan,
    task,
  };
}
