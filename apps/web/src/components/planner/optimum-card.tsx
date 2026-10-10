"use client";

import { money, type Plan } from "../../lib/api/client";
import { planGains } from "./logic";
import { formatSigned } from "./view-model";
import { movesUsedText } from "./moves";
import { transferPairs } from "./view-model";

export function OptimumCard({
  plan,
  keep,
  players,
  cap,
  onShow,
}: {
  plan: Plan | null;
  keep: Plan | null;
  players: Map<number, { name: string }>;
  cap: number | null;
  onShow?: () => void;
}) {
  if (!plan || !keep) {
    return (
      <section className="panel optimum-card">
        <p className="eyebrow">THIS GAMEWEEK</p>
        <h2>Optimum move</h2>
        <p className="muted">Run analysis to see the best move inside your transfer cap. This is scored on this Gameweek, with the horizon total beside it.</p>
      </section>
    );
  }
  const pairs = transferPairs(plan, plan.weeks?.[0]?.event as number | undefined);
  const gains = planGains(plan, keep);
  const used = movesUsedText(pairs.length, cap);
  const name = (id: number) => players.get(id)?.name || `Player ${id}`;
  return (
    <section className="panel optimum-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">THIS GAMEWEEK</p>
          <h2>Optimum move</h2>
        </div>
        {onShow ? <button className="button secondary" type="button" onClick={onShow}>Show on pitch</button> : null}
      </div>
      {pairs.length ? (
        <ul className="transfer-pairs">
          {pairs.map(pair => (
            <li key={`${pair.out}-${pair.in}`}>
              <strong>{name(pair.out)} → {name(pair.in)}</strong>
              <span>Sell {money(pair.sale)}</span>
              <span>Buy {money(pair.purchase)}</span>
              <span>Bank left {money(pair.bank ?? plan.bank_units)}</span>
            </li>
          ))}
        </ul>
      ) : <p>Keep is the best candidate evaluated for this Gameweek.</p>}
      <div className="gain-pair">
        <div>
          <strong>{formatSigned(gains.thisWeek)}</strong>
          <span>this week vs Keep</span>
        </div>
        <div>
          <strong>{formatSigned(gains.horizon)}</strong>
          <span>horizon vs Keep</span>
        </div>
      </div>
      {used ? <p>{used}</p> : null}
      <p className="muted">Best candidate evaluated for this Gameweek inside your cap; bounded search does not guarantee a global optimum. The horizon figure is the same plan over the weeks you asked for.</p>
    </section>
  );
}
