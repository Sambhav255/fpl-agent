"use client";

import { money, type Plan } from "../../lib/api/client";
import { transferPairs } from "./view-model";

export function TransferList({
  plan,
  players,
}: {
  plan: Plan | null;
  players: Map<number, { name: string }>;
}) {
  const pairs = plan ? transferPairs(plan) : [];
  const name = (id: number) => players.get(id)?.name || `Player ${id}`;
  return (
    <section className="panel">
      <p className="eyebrow">THE MOVES</p>
      <h2>Transfers</h2>
      {pairs.length ? (
        <ol className="transfer-pairs">
          {pairs.map((pair) => (
            <li key={`${pair.event ?? "gw"}-${pair.out}-${pair.in}`}>
              <strong>
                {name(pair.out)} → {name(pair.in)}
              </strong>
              <span>{pair.event ? `GW ${pair.event}` : "This plan"}</span>
              <span>Sell {money(pair.sale)}</span>
              <span>Buy {money(pair.purchase)}</span>
              <span>Bank left {money(pair.bank ?? plan?.bank_units)}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p>No transfers in the chosen plan.</p>
      )}
    </section>
  );
}

export function PlanCard({
  plan,
  players,
  busy,
  onSave,
  onShow,
}: {
  plan: Plan;
  players: Map<number, { name: string }>;
  busy: boolean;
  onSave: () => void;
  onShow: () => void;
}) {
  const captainName = players.get(Number(plan.lineup.captain))?.name || "Unknown";
  const unavailable = plan.solver?.net_points_status === "unavailable_unknown_committed_hits";
  return (
    <article className="plan-card">
      <div className="section-heading">
        <h3>{plan.name}</h3>
        <span className="tag">{plan.chip ? plan.chip.replaceAll("_", " ") : "No chip"}</span>
      </div>
      <div className="plan-score">
        <strong>{unavailable ? "Unavailable" : plan.net_points.toFixed(1)}</strong>
        <span>net expected points</span>
        <b>
          {unavailable ? (
            "Unknown committed hits"
          ) : (
            <>
              {plan.delta_to_baseline >= 0 ? "+" : ""}
              {plan.delta_to_baseline.toFixed(1)} vs Keep
            </>
          )}
        </b>
      </div>
      <p>Captain: {captainName}</p>
      <button className="text-button" type="button" onClick={onShow}>
        Show {plan.name} on the pitch
      </button>
      <button className="button secondary" type="button" disabled={busy} onClick={onSave}>
        Save {plan.name}
      </button>
    </article>
  );
}
