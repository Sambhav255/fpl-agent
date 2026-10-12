import { expect, it } from "vitest";
import { withSellMarket } from "../src/components/planner/logic";

it("only explicitly reviewed selling rows acquire a new market anchor", () => {
  const picks = [1, 2].map((player_id) => ({
    player_id,
    position: player_id,
    is_captain: false,
    is_vice_captain: false,
    selling_price_units: 50,
    selling_price_market_units: 50,
    selling_price_provenance: "user_confirmed",
  }));
  const changed = withSellMarket(picks, () => 52, [1]);
  expect(changed[0].selling_price_market_units).toBe(52);
  expect(changed[1]).toBe(picks[1]);
  expect(changed[1].selling_price_market_units).toBe(50);
  expect(withSellMarket(picks, () => 60)).toEqual(picks);
});
