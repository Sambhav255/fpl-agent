"use client";

import { money } from "../../lib/api/client";

export function DeadlineBar({
  deadline,
  bank,
  freeTransfers,
  transfersMade,
  hitPoints,
}: {
  deadline: string;
  bank: string;
  freeTransfers: number | null;
  transfersMade: number | null;
  hitPoints: number | null;
}) {
  return (
    <section className="deadline-bar" aria-label="Gameweek deadline and budget">
      <div>
        <p>Deadline</p>
        <strong>{deadline}</strong>
        <small>Official event deadline, your local time</small>
      </div>
      <div>
        <p>Bank</p>
        <strong>{bank}</strong>
        <small>Confirmed manager input</small>
      </div>
      <div>
        <p>Free transfers</p>
        <strong>{freeTransfers == null ? "Unknown" : freeTransfers}</strong>
        <small>{transfersMade == null ? "Already made unknown" : `${transfersMade} already made`}</small>
      </div>
      <div>
        <p>Hit cost</p>
        <strong>{hitPoints == null ? "Unknown" : `${hitPoints} pts`}</strong>
        <small>One extra transfer costs 4 pts</small>
      </div>
    </section>
  );
}

export function moneyOrUnknown(units: number | null | undefined) {
  return money(units);
}
