"use client";

import { api, teamId, type State } from "../../lib/api/client";
import type { useWorkspace } from "../use-workspace";
import type { usePlannerActions } from "./use-planner-actions";

export function ImportPanel({
  ws,
  task,
}: {
  ws: ReturnType<typeof useWorkspace>;
  task: ReturnType<typeof usePlannerActions>["task"];
}) {
  return (
    <section className="panel import-panel">
      <div>
        <p className="eyebrow">START WITH YOUR SQUAD</p>
        <h2>Bring your team to the touchline.</h2>
        <p>
          Public import shows the last deadline squad. Recent transfers, bank, selling prices, and
          chips may need correction.
        </p>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task("Importing public deadline squad", async (signal) => {
            const manager = await api<State>(
              "/teams/import",
              { team_id: teamId(ws.importValue) },
              "POST",
              signal,
            );
            await ws.loadWorkspace(manager, signal);
            if (!signal.aborted)
              ws.setNotice(
                "Public deadline squad imported. Review current players, finances, and chip state before analysis.",
              );
          });
        }}
      >
        <label htmlFor="team-id">Team ID or official Points page URL</label>
        <div className="inline">
          <input
            id="team-id"
            value={ws.importValue}
            onChange={(event) => ws.setImportValue(event.target.value)}
            placeholder="e.g. 123456"
            required
            disabled={Boolean(ws.busy)}
          />
          <button className="button" type="submit" disabled={Boolean(ws.busy)}>
            Import team
          </button>
        </div>
        <button
          className="text-button"
          type="button"
          disabled={Boolean(ws.busy)}
          onClick={() =>
            void task("Loading synthetic demo", async (signal) => {
              const manager = await api<State>("/demo", {}, "POST", signal);
              await ws.loadWorkspace(manager, signal);
              if (!signal.aborted) {
                ws.setRun(null);
                ws.setRecommendation(null);
                ws.setNotice("Synthetic demo loaded. No real manager data is used.");
              }
            })
          }
        >
          Explore synthetic demo →
        </button>
      </form>
    </section>
  );
}
