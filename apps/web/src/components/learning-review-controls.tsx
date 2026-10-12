"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";

type Schedule = {
  enabled: boolean;
  interval_minutes?: number;
  collect?: boolean;
  include_all?: boolean;
  train?: boolean;
  schedule_version: number;
};
type Review = {
  review_id: string;
  scheduled_for: string;
  promotion: string;
  decisions: { decision_id: string; event: number; status: string }[];
};

export function LearningReviewControls({ teamId, live }: { teamId: number; live: boolean }) {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api<Schedule>(`/teams/${teamId}/learning/schedule`, undefined, "GET", controller.signal),
      api<{ reviews: Review[] }>(
        `/teams/${teamId}/learning/reviews`,
        undefined,
        "GET",
        controller.signal,
      ),
    ])
      .then(([config, result]) => {
        if (!controller.signal.aborted) {
          setSchedule(config);
          setReviews(result.reviews ?? []);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setMessage("Learning reviews could not load.");
      });
    return () => controller.abort();
  }, [teamId]);
  const save = async () => {
    if (!schedule || busy) return;
    setBusy(true);
    setMessage("");
    try {
      const updated = await api<Schedule>(
        `/teams/${teamId}/learning/schedule`,
        {
          enabled: schedule.enabled,
          interval_minutes: schedule.interval_minutes ?? 360,
          collect: schedule.collect ?? false,
          include_all: schedule.include_all ?? false,
          train: schedule.train ?? false,
          expected_version: schedule.schedule_version,
        },
        "PUT",
      );
      setSchedule(updated);
      setMessage("Review schedule saved. The local scheduler and worker must be running.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review schedule could not save.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <section aria-labelledby="learning-review-heading">
      <h3 id="learning-review-heading">Recurring learning reviews</h3>
      <p className="muted">
        Disabled by default. A local review checks finalized outcomes and can collect new data and
        fit an experimental challenger. It keeps the current champion and your manager state.
      </p>
      {!live && <p>Synthetic demos cannot collect official learning outcomes.</p>}
      {schedule ? (
        <fieldset disabled={busy || !live}>
          <legend>Local review schedule</legend>
          <label>
            <input
              type="checkbox"
              checked={schedule.enabled ?? false}
              onChange={(e) => setSchedule({ ...schedule, enabled: e.target.checked })}
            />
            Enable recurring learning reviews
          </label>
          <label>
            Review interval (hours)
            <select
              value={(schedule.interval_minutes ?? 360) / 60}
              onChange={(e) =>
                setSchedule({ ...schedule, interval_minutes: Number(e.target.value) * 60 })
              }
            >
              <option value={1}>Every hour</option>
              <option value={6}>Every six hours</option>
              <option value={24}>Daily</option>
              <option value={168}>Weekly</option>
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={schedule.collect ?? false}
              onChange={(e) =>
                setSchedule({
                  ...schedule,
                  collect: e.target.checked,
                  train: e.target.checked && schedule.train,
                })
              }
            />
            Collect fresh football data
          </label>
          <label>
            <input
              type="checkbox"
              checked={schedule.include_all ?? false}
              disabled={!schedule.collect}
              onChange={(e) => setSchedule({ ...schedule, include_all: e.target.checked })}
            />
            Collect the full current player universe
          </label>
          <label>
            <input
              type="checkbox"
              checked={schedule.train ?? false}
              disabled={!schedule.collect}
              onChange={(e) => setSchedule({ ...schedule, train: e.target.checked })}
            />
            Refit an experimental CatBoost challenger
          </label>
          <button className="button" onClick={save} disabled={busy}>
            Save review schedule
          </button>
        </fieldset>
      ) : !message ? (
        <p role="status">Loading learning reviews…</p>
      ) : null}
      {message && <p role="status">{message}</p>}
      {reviews.length ? (
        reviews.map((review) => (
          <details key={review.review_id}>
            <summary>
              Review {review.scheduled_for}: {review.promotion.replaceAll("_", " ")}
            </summary>
            {review.decisions.map((d) => (
              <p key={d.decision_id}>
                GW {d.event}: {d.status.replaceAll("_", " ")}
              </p>
            ))}
          </details>
        ))
      ) : (
        <p>No completed learning reviews.</p>
      )}
    </section>
  );
}
