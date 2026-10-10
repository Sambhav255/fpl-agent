"use client";

import "./planner.css";
import { money } from "../../lib/api/client";
import { AppChrome } from "../app-chrome";
import { useWorkspace } from "../use-workspace";
import { AnalysisActions, TransferGate } from "./analysis-actions";
import { ImportPanel } from "./import-panel";
import { DeadlineBar } from "./deadline-bar";
import { ChipRow } from "./chip-row";
import { FixtureStrip } from "./fixture-strip";
import { LineupPitch } from "./lineup-pitch";
import { deadlineValue, formatDeadline, transferSettings } from "./logic";
import { movesUsedText } from "./moves";
import { OptimumCard } from "./optimum-card";
import { PlanCard, TransferList } from "./plan-card";
import { SellingPrices } from "./selling-prices";
import { TransferStepper } from "./transfer-stepper";
import { usePlannerActions } from "./use-planner-actions";
import { gameweekOptimum, ids, transferPairs } from "./view-model";

export default function PlannerScreen() {
  const ws = useWorkspace();
  const actions = usePlannerActions(ws);
  const state = ws.state;
  const shown = actions.pitchPlan ?? ws.recommendation?.baseline_plan ?? null;
  const keepHeading = Boolean(
    ws.recommendation && shown && shown.plan_id === ws.recommendation.baseline_plan.plan_id,
  );
  const title = ws.recommendation
    ? keepHeading
      ? "Suggested Keep lineup"
      : shown?.name || "Suggested Keep lineup"
    : "Your current lineup";
  const starters = shown
    ? ids(shown.lineup.starters)
    : state?.picks
        .filter((pick) => pick.position <= 11)
        .sort((a, b) => a.position - b.position)
        .map((pick) => pick.player_id) || [];
  const bench = shown
    ? ids(shown.lineup.bench)
    : state?.picks
        .filter((pick) => pick.position > 11)
        .sort((a, b) => a.position - b.position)
        .map((pick) => pick.player_id) || [];
  const captain =
    Number(shown?.lineup.captain || state?.picks.find((pick) => pick.is_captain)?.player_id || 0) ||
    undefined;
  const vice =
    Number(
      shown?.lineup.vice_captain ||
        state?.picks.find((pick) => pick.is_vice_captain)?.player_id ||
        0,
    ) || undefined;
  const usedNote = shown
    ? movesUsedText(
        transferPairs(shown, state?.next_event).length,
        actions.resolved.max_transfers_this_event,
      )
    : null;
  const plans = ws.recommendation
    ? [ws.recommendation.baseline_plan, ...ws.recommendation.alternatives]
    : [];
  const optimum = gameweekOptimum(ws.recommendation);
  return (
    <AppChrome
      season={state?.season}
      dataMode={state?.data_mode}
      busy={ws.busy}
      progress={ws.progress}
      activeJob={ws.activeJob}
      error={ws.error}
      notice={ws.notice}
      dirty={ws.dirty}
      stale={ws.stale}
      onCancel={ws.cancelJob}
    >
      <div className="page-heading">
        <div>
          <p className="eyebrow">PLAN WITH A CLEARER PICTURE</p>
          <h1>Planner</h1>
          <p className="muted">
            {state
              ? `Gameweek ${state.next_event} · ${state.data_mode === "demo" ? "Synthetic squad" : `Team ${state.team_id}`} · State v${state.state_version}`
              : "Import your team or explore a clearly labelled synthetic demo."}
          </p>
        </div>
        <AnalysisActions
          transfersAllowed={actions.transfersAllowed}
          busy={Boolean(ws.busy)}
          dirty={ws.dirty}
          stale={ws.stale}
          hasState={Boolean(state)}
          onRun={() => actions.analyse("transfers")}
          onLineup={() => actions.analyse("lineup")}
        />
      </div>
      {state ? (
        <div className="planner">
          <DeadlineBar
            deadline={formatDeadline(deadlineValue(ws.status))}
            bank={money(state.bank_units)}
            freeTransfers={actions.free}
            transfersMade={actions.made}
            hitPoints={state.confirmed_hit_points ?? null}
          />
          <TransferStepper
            freeTransfers={actions.free}
            transfersMade={actions.made}
            count={actions.count}
            allowHit={actions.allowHit}
            disabled={Boolean(ws.busy)}
            onCount={(next) =>
              actions.changeSettings(
                transferSettings({
                  count: next,
                  allowHit: actions.allowHit,
                  free: actions.free,
                  made: actions.made,
                }),
              )
            }
            onAllowHit={(next) =>
              actions.changeSettings(
                transferSettings({
                  count: actions.count ?? 0,
                  allowHit: next,
                  free: actions.free,
                  made: actions.made,
                }),
              )
            }
          />
          <TransferGate reason={actions.transfersAllowed ? null : actions.blockReason} />
          {usedNote ? (
            <p className="feedback success" role="status">
              {usedNote}
            </p>
          ) : null}
          <section className="panel">
            <h2>Planning constraints</h2>
            <div className="form-grid">
              <label>
                Horizon (Gameweeks)
                <input
                  type="number"
                  min={1}
                  max={8}
                  value={ws.settings.horizon_events}
                  disabled={Boolean(ws.busy)}
                  onChange={(event) =>
                    actions.changeSettings({ horizon_events: Number(event.target.value) })
                  }
                />
              </label>
              <label>
                Solver limit (seconds)
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={ws.settings.solver_time_limit_seconds}
                  disabled={Boolean(ws.busy)}
                  onChange={(event) =>
                    actions.changeSettings({
                      solver_time_limit_seconds: Number(event.target.value),
                    })
                  }
                />
              </label>
            </div>
            <p className="muted">
              The forecast is the labelled approximate baseline. Transfers and chips stay manual.
            </p>
          </section>
          {actions.suggestionNote ? <p className="muted">{actions.suggestionNote}</p> : null}
          <SellingPrices
            key={`${state.team_id}-${state.state_version}`}
            picks={state.picks}
            players={ws.playerMap}
            suggestions={actions.suggestions}
            disabled={Boolean(ws.busy)}
            onAccept={actions.acceptPrices}
          />
          <OptimumCard
            plan={optimum}
            keep={ws.recommendation?.baseline_plan ?? null}
            players={ws.playerMap}
            cap={actions.resolved.max_transfers_this_event}
            onShow={optimum ? () => actions.setPitchPlan(optimum) : undefined}
          />
          {optimum ? (
            <button
              className="button secondary"
              disabled={Boolean(ws.busy) || ws.stale || ws.dirty}
              onClick={() => actions.savePlan(optimum)}
            >
              Save this-week plan
            </button>
          ) : null}
          <LineupPitch
            title={title}
            event={state.next_event}
            starters={starters}
            bench={bench}
            captain={captain}
            vice={vice}
            players={ws.playerMap}
            picks={state.picks}
            points={ws.points}
            fixtures={ws.run?.fixtures || []}
          />
          <TransferList plan={shown} players={ws.playerMap} />
          <FixtureStrip
            playerIds={[...starters, ...bench]}
            players={ws.playerMap}
            fixtures={ws.run?.fixtures || []}
            fromEvent={state.next_event}
          />
          <ChipRow
            chips={state.chips || {}}
            recommendation={ws.recommendation}
            busy={Boolean(ws.busy)}
            disabled={!actions.transfersAllowed || ws.dirty || ws.stale}
            onRunChip={(chip) => actions.analyse("transfers", { chip_policy: chip })}
          />
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">COMPARE THE OPTIONS</p>
                <h2>Plans, with the trade-offs visible.</h2>
              </div>
            </div>
            {plans.length ? (
              <div className="plan-grid">
                {plans.map((plan) => (
                  <PlanCard
                    key={plan.plan_id}
                    plan={plan}
                    players={ws.playerMap}
                    busy={Boolean(ws.busy) || ws.dirty || ws.stale}
                    onShow={() => actions.setPitchPlan(plan)}
                    onSave={() => actions.savePlan(plan)}
                  />
                ))}
              </div>
            ) : (
              <div className="empty">
                <span aria-hidden="true">↗</span>
                <h3>Your next move is still an open question.</h3>
                <p>
                  Run analysis to compare Keep with validated alternatives. No recommendations are
                  shown before computation.
                </p>
              </div>
            )}
          </section>
        </div>
      ) : (
        <ImportPanel ws={ws} task={actions.task} />
      )}
    </AppChrome>
  );
}
