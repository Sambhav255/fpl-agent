"use client";

import type { Settings } from "../../lib/api/client";
import { chipLabel, readChipAdvice } from "./view-model";
import type { Recommendation } from "../../lib/api/client";

const ORDER = ["wildcard", "free_hit", "bench_boost", "triple_captain"] as const;

export function ChipRow({
  chips,
  recommendation,
  busy,
  disabled,
  onRunChip,
}: {
  chips: Record<string, boolean | null | undefined>;
  recommendation: Recommendation | null;
  busy: boolean;
  disabled: boolean;
  onRunChip: (chip: Settings["chip_policy"]) => void;
}) {
  const advice = readChipAdvice(recommendation);
  return (
    <section className="panel">
      <p className="eyebrow">CHIP TIMING</p>
      <h2>Chips</h2>
      <p className="muted">
        Play or save is for this week against other weeks in the horizon. It is not a season-long
        optimum. Nothing is submitted to FPL.
      </p>
      <ul className="chip-row">
        {ORDER.map((chip) => {
          const note = advice.find((item) => item.chip === chip);
          const inventory = chips[chip];
          const status =
            note?.status ??
            (inventory === false ? "used" : inventory === true ? "not_evaluated" : "unavailable");
          const runnable = chip === "wildcard" || chip === "free_hit";
          return (
            <li key={chip}>
              <h3>{chipLabel(chip)}</h3>
              <span className="tag">{status.replaceAll("_", " ")}</span>
              <p>
                {note?.reason ||
                  (status === "used"
                    ? "Already used."
                    : status === "unavailable"
                      ? "Unavailable or unknown in this window."
                      : "Not evaluated on this run.")}
              </p>
              {note && (note.this_week_points != null || note.comparison_points != null) ? (
                <p>
                  This week {note.this_week_points ?? "Unknown"} · comparison{" "}
                  {note.comparison_points ?? "Unknown"}
                </p>
              ) : null}
              {runnable ? (
                <button
                  className="button secondary"
                  type="button"
                  disabled={busy || disabled || status === "used"}
                  onClick={() => onRunChip(chip)}
                >
                  {chipLabel(chip)}
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
