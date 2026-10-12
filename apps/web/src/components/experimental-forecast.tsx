"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, waitForJob, type Player, type Run } from "../lib/api/client";
import { preferredTeamId } from "../lib/profile";

type Collection = { collection_id: string; captured_at: string; player_count: number };

export function ExperimentalForecast({ artifactId }: { artifactId?: string }) {
  const [teamId, setTeamId] = useState("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collectionId, setCollectionId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [baseline, setBaseline] = useState<Run | null>(null);
  const [names, setNames] = useState<Record<number, string>>({});
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const request = new AbortController();
    api<{ collections: Collection[] }>("/data/collections", undefined, "GET", request.signal)
      .then((result) => {
        setTeamId((current) => current || preferredTeamId() || "");
        const ordered = result.collections
          .filter((collection) => collection.player_count > 0)
          .sort((a, b) => b.captured_at.localeCompare(a.captured_at));
        setCollections(ordered);
        setCollectionId(ordered[0]?.collection_id ?? "");
      })
      .catch(() => {
        if (!request.signal.aborted) setError("Retained collections could not load.");
      });
    return () => {
      request.abort();
      controller.current?.abort();
    };
  }, []);
  async function forecast() {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setBusy(true);
    setError("");
    setRun(null);
    setBaseline(null);
    try {
      const bundle = await api<{ serving_bundle_id: string }>(
        "/projections/bundles",
        {
          team_id: Number(teamId),
          artifact_id: artifactId,
          collection_id: collectionId,
        },
        "POST",
        request.signal,
      );
      const job = await api<{ job_id: string }>(
        "/projections/runs",
        {
          team_id: Number(teamId),
          provider: "football_catboost",
          mode: "experimental",
          artifact_id: artifactId,
          serving_bundle_id: bundle.serving_bundle_id,
          horizon_events: 1,
        },
        "POST",
        request.signal,
      );
      const result = await waitForJob<Run>(job.job_id, () => {}, request.signal);
      const [baselineJob, catalog] = await Promise.all([
        api<{ job_id: string }>(
          "/projections/runs",
          {
            team_id: Number(teamId),
            provider: "baseline",
            horizon_events: 1,
          },
          "POST",
          request.signal,
        ),
        api<{ players: Player[] }>("/players?data_mode=live", undefined, "GET", request.signal),
      ]);
      const comparison = await waitForJob<Run>(baselineJob.job_id, () => {}, request.signal);
      if (!request.signal.aborted) {
        setNames(
          Object.fromEntries(catalog.players.map((player) => [player.player_id, player.name])),
        );
        setBaseline(comparison);
        setRun(result);
      }
    } catch (failure) {
      if (!request.signal.aborted)
        setError(failure instanceof Error ? failure.message : "Forecast failed.");
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>Experimental football forecast</h2>
      <p>
        One-gameweek challenger, using a limited player universe. It has not passed default
        promotion. Your current squad and financial state must be reviewed first.
      </p>
      <label>
        Team ID
        <input
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          inputMode="numeric"
          disabled={busy}
        />
      </label>
      <label>
        Retained observations
        <select
          value={collectionId}
          onChange={(e) => setCollectionId(e.target.value)}
          disabled={busy}
        >
          <option value="">Choose a collection</option>
          {collections.map((c) => (
            <option key={c.collection_id} value={c.collection_id}>
              {c.captured_at} · {c.player_count} players
            </option>
          ))}
        </select>
      </label>
      <p>Artifact: {artifactId ?? "Unavailable"}</p>
      <button
        disabled={busy || !artifactId || !collectionId || !/^[1-9]\d*$/.test(teamId)}
        onClick={() => void forecast()}
      >
        {busy ? "Running experimental forecast…" : "Run experimental forecast"}
      </button>
      {error && <p role="alert">{error}</p>}
      {busy && <p role="status">Validating retained observations and running the worker.</p>}
      {run && (
        <div>
          <p>
            Completed: {run.model_family} · {run.model_status} · {run.projections.length} fixture
            forecasts.
          </p>
          <p>Run reference: {run.projection_run_id}</p>
          <p>{(run.warnings ?? []).join(" · ")}</p>
          <table>
            <caption>
              Per-fixture expected points; experimental means are not confidence guarantees.
            </caption>
            <thead>
              <tr>
                <th>Player</th>
                <th>Fixture</th>
                <th>Baseline</th>
                <th>CatBoost</th>
                <th>Minutes</th>
              </tr>
            </thead>
            <tbody>
              {run.projections.map((projection) => {
                const comparator = baseline?.projections.find(
                  (item) =>
                    item.player_id === projection.player_id &&
                    item.fixture_id === projection.fixture_id,
                );
                return (
                  <tr key={`${projection.player_id}-${projection.fixture_id}`}>
                    <td>{names[projection.player_id] ?? projection.player_id}</td>
                    <td>{projection.fixture_id}</td>
                    <td>{comparator?.expected_points.toFixed(2) ?? "Unavailable"}</td>
                    <td>{projection.expected_points.toFixed(2)}</td>
                    <td>{projection.expected_minutes.toFixed(0)}</td>
                  </tr>
                );
              })}
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
