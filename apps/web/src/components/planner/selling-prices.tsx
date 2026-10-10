"use client";

import { useCallback, useState } from "react";
import { money, type Pick, type Player } from "../../lib/api/client";
import { MoneyInput } from "../editors";
import { pickSaleConfirmed, type PriceDecision } from "./logic";
import type { PriceSuggestion } from "./types";

type Draft = {
  units: number | null;
  kind: "purchase" | "sell";
  rejected: boolean;
  revision: number;
};

export function SellingPrices({
  picks,
  players,
  suggestions,
  disabled,
  onAccept,
}: {
  picks: Pick[];
  players: Map<number, Player>;
  suggestions: PriceSuggestion[];
  disabled?: boolean;
  onAccept: (decisions: PriceDecision[]) => void;
}) {
  const [invalidRows, setInvalidRows] = useState<Record<string, boolean>>({});
  const reportValidity = useCallback(
    (name: string, invalid: boolean) =>
      setInvalidRows((previous) =>
        previous[name] === invalid ? previous : { ...previous, [name]: invalid },
      ),
    [],
  );
  const [draft, setDraft] = useState<Record<number, Draft>>({});
  const pending = picks.filter((pick) => !pickSaleConfirmed(pick));
  if (!pending.length) {
    return (
      <section className="panel">
        <h2>Selling prices</h2>
        <p role="status">Selling prices are confirmed.</p>
      </section>
    );
  }
  const suggestionFor = (playerId: number) =>
    suggestions.find((item) => item.player_id === playerId);
  const row = (playerId: number): Draft =>
    draft[playerId] ?? { units: null, kind: "sell", rejected: false, revision: 0 };
  const decisions = (): PriceDecision[] =>
    pending.map((pick) => {
      const current = row(pick.player_id);
      return {
        player_id: pick.player_id,
        units: current.rejected ? null : current.units,
        kind: current.kind,
        rejected: current.rejected,
      };
    });
  const ready = decisions().some((decision) => decision.rejected || decision.units != null);
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">CONFIRM BEFORE YOU SEARCH</p>
          <h2>Selling prices</h2>
        </div>
        <button
          className="button"
          type="button"
          disabled={disabled || !ready || Object.values(invalidRows).some(Boolean)}
          onClick={() =>
            onAccept(decisions().filter((decision) => decision.rejected || decision.units != null))
          }
        >
          Accept selling prices
        </button>
      </div>
      <p className="muted">
        Estimates stay unknown until you accept them. Blank rows are left unknown. Prices use £0.1m
        steps.
      </p>
      <ul className="price-list">
        {pending.map((pick) => {
          const player = players.get(pick.player_id);
          const suggestion = suggestionFor(pick.player_id);
          const current = row(pick.player_id);
          const estimateUnits =
            suggestion?.selling_price_units ?? suggestion?.purchase_price_units ?? null;
          const estimateKind: "purchase" | "sell" =
            suggestion?.selling_price_units != null ? "sell" : "purchase";
          return (
            <li key={pick.player_id}>
              <div>
                <strong>{player?.name || `Player ${pick.player_id}`}</strong>
                <span className="muted">Market {money(player?.market_price_units)}</span>
                {estimateUnits != null ? (
                  <span className="tag">Estimate {money(estimateUnits)} · not confirmed</span>
                ) : (
                  <span className="muted">No estimate published</span>
                )}
              </div>
              <div className="price-edit">
                <label className="kind-select">
                  Price kind
                  <select
                    aria-label={`Price kind for ${player?.name || pick.player_id}`}
                    value={current.kind}
                    disabled={disabled || current.rejected}
                    onChange={(event) =>
                      setDraft((previous) => ({
                        ...previous,
                        [pick.player_id]: { ...current, kind: event.target.value as Draft["kind"] },
                      }))
                    }
                  >
                    <option value="sell">Selling price</option>
                    <option value="purchase">Purchase price</option>
                  </select>
                </label>
                <MoneyInput
                  onValidity={reportValidity}
                  key={`${pick.player_id}-${current.revision}`}
                  label={`Confirm price for ${player?.name || pick.player_id}`}
                  value={current.units}
                  onChange={(units) =>
                    setDraft((previous) => ({
                      ...previous,
                      [pick.player_id]: { ...current, units, rejected: false },
                    }))
                  }
                />
                {estimateUnits != null ? (
                  <button
                    className="text-button"
                    type="button"
                    disabled={disabled}
                    onClick={() =>
                      setDraft((previous) => ({
                        ...previous,
                        [pick.player_id]: {
                          units: estimateUnits,
                          kind: estimateKind,
                          rejected: false,
                          revision: current.revision + 1,
                        },
                      }))
                    }
                  >
                    Use estimate
                  </button>
                ) : null}
                <button
                  className="text-button"
                  type="button"
                  disabled={disabled}
                  onClick={() =>
                    setDraft((previous) => ({
                      ...previous,
                      [pick.player_id]: {
                        units: null,
                        kind: current.kind,
                        rejected: true,
                        revision: current.revision + 1,
                      },
                    }))
                  }
                >
                  Reject
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
