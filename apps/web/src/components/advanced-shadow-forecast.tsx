"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { api, waitForJob, type Run } from "../lib/api/client";
import { preferredTeamId } from "../lib/profile";

type Bundle = {
  serving_bundle_id: string;
  provider: string;
  artifact_id: string;
  horizon_events: number;
  prediction_origin: string;
};

function subscribeProfile(listener: () => void) {
  window.addEventListener("storage", listener);
  return () => window.removeEventListener("storage", listener);
}

function profileSnapshot() {
  return preferredTeamId() || "";
}

function serverProfileSnapshot() {
  return "";
}

export function AdvancedShadowForecast() {
  const preferred = useSyncExternalStore(subscribeProfile, profileSnapshot, serverProfileSnapshot);
  const [teamDraft, setTeamId] = useState<string | null>(null);
  const teamId = teamDraft ?? preferred;
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function load() {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setBusy("Checking reviewed shadow models…");
    setError("");
    setRun(null);
    setBundles([]);
    setSelected("");
    try {
      const result = await api<{ bundles: Bundle[] }>(
        `/projections/bundles?team_id=${Number(teamId)}`,
        undefined,
        "GET",
        request.signal,
      );
      if (!request.signal.aborted) {
        setBundles(result.bundles);
        setSelected(result.bundles[0]?.serving_bundle_id ?? "");
      }
    } catch (failure) {
      if (!request.signal.aborted)
        setError(failure instanceof Error ? failure.message : "Shadow models could not load.");
    } finally {
      if (!request.signal.aborted) setBusy("");
    }
  }

  async function forecast() {
    const bundle = bundles.find((item) => item.serving_bundle_id === selected);
    if (!bundle) return;
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setBusy("Queueing shadow forecast…");
    setError("");
    setRun(null);
    try {
      const job = await api<{ job_id: string }>(
        "/projections/runs",
        {
          team_id: Number(teamId),
          provider: bundle.provider,
          mode: "shadow",
          artifact_id: bundle.artifact_id,
          serving_bundle_id: bundle.serving_bundle_id,
          horizon_events: bundle.horizon_events,
        },
        "POST",
        request.signal,
      );
      const result = await waitForJob<Run>(
        job.job_id,
        (status) => {
          if (!request.signal.aborted) setBusy(`Shadow forecast: ${status.status}`);
        },
        request.signal,
      );
      if (!request.signal.aborted) setRun(result);
    } catch (failure) {
      if (!request.signal.aborted)
        setError(failure instanceof Error ? failure.message : "Shadow forecast failed.");
    } finally {
      if (!request.signal.aborted) setBusy("");
    }
  }

  return (
    <section className="panel">
      <h2>Advanced shadow forecasts</h2>
      <p>
        Compare reviewed Bayesian, TFT or mean-ensemble forecasts in shadow. Baseline remains the
        default; research results do not establish an advantage or calibrated confidence.
      </p>
      <label>
        Shadow team ID
        <input
          value={teamId}
          inputMode="numeric"
          disabled={Boolean(busy)}
          onChange={(event) => {
            setTeamId(event.target.value);
            setBundles([]);
            setSelected("");
            setRun(null);
            setError("");
          }}
        />
      </label>
      <button disabled={Boolean(busy) || !/^[1-9]\d*$/.test(teamId)} onClick={() => void load()}>
        Load reviewed shadow models
      </button>
      <label>
        Reviewed shadow model
        <select
          value={selected}
          disabled={Boolean(busy) || bundles.length === 0}
          onChange={(event) => {
            setSelected(event.target.value);
            setRun(null);
          }}
        >
          <option value="">No reviewed model selected</option>
          {bundles.map((bundle) => (
            <option key={bundle.serving_bundle_id} value={bundle.serving_bundle_id}>
              {bundle.provider} · {bundle.horizon_events} events · {bundle.artifact_id}
            </option>
          ))}
        </select>
      </label>
      <button disabled={Boolean(busy) || !selected} onClick={() => void forecast()}>
        Run shadow forecast
      </button>
      {bundles.length === 0 && (
        <p>
          Models need locally reviewed sources and a registered current input bundle before use.
        </p>
      )}
      {busy && <p role="status">{busy}</p>}
      {error && <p role="alert">{error}</p>}
      {run && (
        <div>
          <p>
            Shadow completed: {run.model_family} · {run.horizon_events} events ·{" "}
            {run.projections.length} fixture forecasts.
          </p>
          <p>{(run.warnings ?? []).join(" · ")}</p>
          <p>Run reference: {run.projection_run_id}</p>
          <table>
            <caption>Unconditional fixture means; no default promotion</caption>
            <thead>
              <tr>
                <th>Player</th>
                <th>Fixture</th>
                <th>Event</th>
                <th>Expected points</th>
                <th>Expected minutes</th>
              </tr>
            </thead>
            <tbody>
              {run.projections.map((projection) => (
                <tr key={`${projection.player_id}-${projection.fixture_id}`}>
                  <td>{projection.player_id}</td>
                  <td>{projection.fixture_id}</td>
                  <td>{projection.event}</td>
                  <td>{projection.expected_points.toFixed(2)}</td>
                  <td>{projection.expected_minutes.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p>
        <Link href="/settings">Review manager state</Link>
      </p>
    </section>
  );
}
