import { expect, it } from "vitest";
import type { State } from "../src/lib/api/client";
import { reviewNewEvent } from "../src/lib/manager-review";

it("new event clears private confirmations without editing saved state or inventing zeros", () => {
  const state: State = {
    team_id: 0,
    state_version: 1,
    season: "2026/27",
    data_mode: "demo",
    snapshot_id: "synthetic-fixture",
    current_chip_confirmed: true,
    club_limit_exception: false,
    next_event: 6,
    bank_units: 7,
    free_transfers_at_event_start: 3,
    transfers_made_this_event: 0,
    confirmed_hit_points: 0,
    chips: { wildcard: true },
    picks: [
      {
        player_id: 1,
        position: 1,
        purchase_price_units: 60,
        selling_price_units: 63,
        selling_price_provenance: "user_confirmed",
        is_captain: true,
        is_vice_captain: false,
      },
    ],
  };
  const next = reviewNewEvent(state, 7);
  expect(next.bank_units).toBeNull();
  expect(next.free_transfers_at_event_start).toBeNull();
  expect(next.transfers_made_this_event).toBeNull();
  expect(next.confirmed_hit_points).toBeNull();
  expect(next.current_chip_confirmed).toBe(false);
  expect(next.chips?.wildcard).toBeNull();
  expect(next.picks[0].selling_price_units).toBeNull();
  expect(next.picks[0].purchase_price_units).toBe(60);
  expect(state.bank_units).toBe(7);
  expect(state.picks[0].selling_price_units).toBe(63);
  expect(reviewNewEvent(state, 6)).toBe(state);
});
