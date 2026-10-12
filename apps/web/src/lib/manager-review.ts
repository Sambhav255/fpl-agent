import type { State } from "./api/client";

/** A new event needs fresh private confirmations; this edits a draft only. */
export function reviewNewEvent(state: State, event: number): State {
  if (event === state.next_event) return state;
  return {
    ...state,
    next_event: event,
    bank_units: null,
    free_transfers_at_event_start: null,
    transfers_made_this_event: null,
    confirmed_hit_points: null,
    financial_provenance: {},
    financial_confirmed_at: null,
    current_chip: null,
    current_chip_confirmed: false,
    chips: Object.fromEntries(
      Object.keys(state.chips ?? {}).map((chip) => [
        chip,
        state.chips?.[chip] === false ? false : null,
      ]),
    ),
    event_start_picks: null,
    event_start_bank_units: null,
    picks: state.picks.map((pick) => ({
      ...pick,
      selling_price_units: null,
      selling_price_market_units: null,
      selling_price_provenance: "unknown",
      confirmed_at: null,
    })),
    warnings: [
      ...(state.warnings ?? []),
      "New gameweek: review squad, selling prices, bank, transfers, hits and chips. Review persistent squad if Free Hit was used.",
    ],
  };
}
