"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";

type Status = {
  champion: string;
  rl_installed: boolean;
  policies: {
    artifact_id: string;
    status: string;
    seed_count?: number;
    distinct_test_paths?: number;
    evidence_modes?: string[];
  }[];
};

export function StrategyStatus() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api<Status>("/strategy/status", undefined, "GET", controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setStatus(value);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError("Strategy registry unavailable.");
      });
    return () => controller.abort();
  }, []);
  return (
    <section className="panel">
      <h2>Strategy research</h2>
      <p>
        The numerical planner remains the strategy champion. RL experiments select legal paper
        actions and require prospective evidence before promotion.
      </p>
      {error ? (
        <p role="status">{error}</p>
      ) : !status ? (
        <p role="status">Loading strategy research…</p>
      ) : (
        <>
          <p>Optional RL libraries: {status.rl_installed ? "installed" : "unavailable"}.</p>
          {(status.policies ?? []).length === 0 ? (
            <p>No trained policy artifact is retained.</p>
          ) : (
            <ul>
              {status.policies.map((policy) => (
                <li key={policy.artifact_id}>
                  {policy.artifact_id}: {policy.status.replaceAll("_", " ")} ·{" "}
                  {policy.seed_count ?? "unknown"} seeds · {policy.distinct_test_paths ?? "unknown"}{" "}
                  distinct test paths. Evidence:{" "}
                  {(policy.evidence_modes ?? []).join(", ") || "unavailable"}. Shadow only.
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
