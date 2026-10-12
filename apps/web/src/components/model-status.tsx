"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import { AppChrome } from "./app-chrome";
import { StrategyStatus } from "./strategy-status";
import { ExperimentalForecast } from "./experimental-forecast";
import { AdvancedShadowForecast } from "./advanced-shadow-forecast";

type Model = {
  model_family: string;
  status: string;
  reason: string | string[];
  active?: boolean;
  strict_release_eligible?: boolean;
  evaluation_kind?: string;
  artifact_id?: string;
  metrics?: { mae?: number; rmse?: number; n?: number } | null;
  artifacts?: { artifact_id: string; status: string }[];
};

export default function ModelStatus() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<{ models: Model[] }>("/models", undefined, "GET", controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setModels(result.models);
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted)
          setError(failure instanceof Error ? failure.message : "Model registry could not load.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [attempt]);
  return (
    <AppChrome
      season={undefined}
      dataMode={undefined}
      busy={loading ? "Loading model registry" : ""}
      progress={0}
      activeJob={null}
      error={error}
      notice=""
      dirty={false}
      stale={false}
      onCancel={() => {}}
    >
      <div className="page-heading">
        <div>
          <p className="eyebrow">FORECAST PROVENANCE</p>
          <h1>Models</h1>
          <p>Training, evaluation and active prediction status, independent of your team.</p>
        </div>
        <button
          onClick={() => {
            setLoading(true);
            setError("");
            setAttempt((value) => value + 1);
          }}
          disabled={loading}
        >
          Refresh model status
        </button>
      </div>
      <section className="panel">
        <h2>Model registry</h2>
        <p>
          The approximate baseline currently powers recommendations. Advanced pipelines require
          verified historical inputs and chronological evaluation before activation.
        </p>
        {loading && <p role="status">Loading model registry…</p>}
        {!loading && !error && models.length === 0 && <p>No models were returned by the API.</p>}
        <div className="model-grid">
          {models.map((model) => (
            <article className="panel" key={model.model_family}>
              <h3>
                {model.model_family === "tft_multilead"
                  ? "Multilead TFT (research)"
                  : model.model_family === "ensemble"
                    ? "Mean ensemble (research)"
                    : model.model_family === "tft"
                      ? "Temporal Fusion Transformer"
                      : model.model_family === "football_catboost"
                        ? "Football CatBoost (experimental)"
                        : model.model_family === "catboost"
                          ? "CatBoost"
                          : model.model_family === "bayesian"
                            ? "Bayesian events"
                            : "Baseline"}
              </h3>
              <p>
                <strong>{model.status.replaceAll("_", " ")}</strong> ·{" "}
                {model.status === "active" || model.active === true
                  ? "Used for predictions"
                  : "Inactive for predictions"}
              </p>
              {model.evaluation_kind === "retrospective_unverified" && (
                <p>
                  Retrospective diagnostic only. Historical publication timing is unverified; this
                  artifact is ineligible for live recommendations.
                </p>
              )}
              {model.evaluation_kind === "retrospective_assumed" && (
                <p>
                  Historical timing is assumed. This experiment is not promoted; its scores do not
                  establish an improvement over the baseline.
                </p>
              )}
              {Array.isArray(model.reason) ? (
                <ul>
                  {model.reason.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              ) : (
                <p>{model.reason}</p>
              )}
              {model.metrics && (
                <p>
                  Diagnostic evaluation: {model.metrics.n ?? "unknown"} rows · MAE{" "}
                  {model.metrics.mae?.toFixed(3) ?? "unavailable"} · RMSE{" "}
                  {model.metrics.rmse?.toFixed(3) ?? "unavailable"}. These metrics do not establish
                  live strategy improvement.
                </p>
              )}
              {model.artifacts && model.artifacts.length > 0 && (
                <ul aria-label="Retained research artifacts">
                  {model.artifacts.map((artifact) => (
                    <li key={artifact.artifact_id}>
                      {artifact.artifact_id}: {artifact.status.replaceAll("_", " ")}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>
      </section>
      <StrategyStatus />
      <AdvancedShadowForecast />
      <ExperimentalForecast
        artifactId={
          models.find(
            (model) =>
              model.model_family === "football_catboost" &&
              model.status === "evaluated_experimental",
          )?.artifact_id
        }
      />
    </AppChrome>
  );
}
