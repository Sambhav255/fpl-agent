import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { TransferStepper } from "../src/components/planner/transfer-stepper";
import { SellingPrices } from "../src/components/planner/selling-prices";
import { transferSettings, transferSearchAllowed } from "../src/components/planner/logic";
import type { Pick, Player } from "../src/lib/api/client";
afterEach(cleanup);
it("caps the stepper at remaining free moves and makes a hit explicit", () => {
  const change = vi.fn();
  render(
    <TransferStepper
      freeTransfers={3}
      transfersMade={0}
      count={3}
      allowHit={false}
      onCount={change}
      onAllowHit={vi.fn()}
    />,
  );
  expect(screen.getByRole("button", { name: "More transfers" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Fewer transfers" }));
  expect(change).toHaveBeenCalledWith(2);
  expect(transferSettings({ count: 1, allowHit: false, free: 3, made: 0 })).toEqual({
    max_transfers_this_event: 1,
    max_additional_hit_points: 0,
  });
  expect(transferSettings({ count: 3, allowHit: true, free: 3, made: 0 })).toEqual({
    max_transfers_this_event: 4,
    max_additional_hit_points: 4,
  });
});
it("blocks unaccepted estimates and preserves selling versus purchase kind", () => {
  const accept = vi.fn();
  const pick = {
    player_id: 1,
    purchase_price_units: null,
    selling_price_units: null,
    selling_price_provenance: "unknown",
    position: 1,
    is_captain: false,
    is_vice_captain: false,
  } as Pick;
  const player = { player_id: 1, name: "Sensitive", market_price_units: 56 } as Player;
  expect(transferSearchAllowed({ bank: 7, free: 3, made: 0, hits: 0, picks: [pick] })).toBe(false);
  render(
    <SellingPrices
      picks={[pick]}
      players={new Map([[1, player]])}
      suggestions={[
        {
          player_id: 1,
          purchase_price_units: 55,
          selling_price_units: 55,
          provenance: "published_gameweek_price_estimate",
        },
      ]}
      onAccept={accept}
    />,
  );
  expect(screen.getByRole("button", { name: "Accept selling prices" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Use estimate" }));
  expect(screen.getByLabelText("Price kind for Sensitive")).toHaveValue("sell");
  fireEvent.change(screen.getByLabelText("Confirm price for Sensitive"), {
    target: { value: "1.55" },
  });
  expect(screen.getByRole("button", { name: "Accept selling prices" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Confirm price for Sensitive"), {
    target: { value: "5.5" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Accept selling prices" }));
  expect(accept).toHaveBeenCalledWith([{ player_id: 1, units: 55, kind: "sell", rejected: false }]);
});
