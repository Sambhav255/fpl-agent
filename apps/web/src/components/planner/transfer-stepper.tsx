"use client";

import { remainingFreeTransfers } from "./logic";

export function TransferStepper({
  freeTransfers,
  transfersMade,
  count,
  allowHit,
  disabled = false,
  onCount,
  onAllowHit,
}: {
  freeTransfers: number | null;
  transfersMade: number | null;
  count: number | null;
  allowHit: boolean;
  disabled?: boolean;
  onCount: (count: number) => void;
  onAllowHit: (allow: boolean) => void;
}) {
  const remaining = remainingFreeTransfers(freeTransfers, transfersMade);
  const known = remaining != null && count != null;
  return (
    <section className="panel planner-stepper" aria-labelledby="transfer-count-label">
      <div className="section-heading">
        <div>
          <p className="eyebrow">THIS GAMEWEEK</p>
          <h2 id="transfer-count-label">Transfers this Gameweek</h2>
        </div>
        <p className="muted">{known ? `${remaining} free still available` : "Free transfers unknown"}</p>
      </div>
      <div className="stepper-row">
        <button type="button" className="button secondary" aria-label="Fewer transfers" disabled={disabled || !known || count <= 0} onClick={() => onCount(count! - 1)}>−</button>
        <output aria-labelledby="transfer-count-label">{known ? count : "Unknown"}</output>
        <button type="button" className="button secondary" aria-label="More transfers" disabled={disabled || !known || count >= remaining!} onClick={() => onCount(count! + 1)}>+</button>
        <label className="checkbox hit-toggle">
          <input type="checkbox" checked={allowHit} disabled={disabled} onChange={event => onAllowHit(event.target.checked)} />
          Allow one hit
        </label>
      </div>
      <p className="muted">The solver can use fewer transfers than this cap. One hit costs 4 points and allows one extra move.</p>
    </section>
  );
}
