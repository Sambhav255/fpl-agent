import type { Plan, Recommendation, Settings } from "../../lib/api/client";

/** Local extension while the generated schema may still be catching up. */
export type ChipAdviceStatus = "used" | "unavailable" | "save" | "play_this_week" | "not_evaluated";

export type ChipAdvice = {
  chip: string;
  status: ChipAdviceStatus;
  this_week_points: number | null;
  comparison_points: number | null;
  reason: string;
};

export type PlannerSettings = Settings & {
  /** null means the solver applies no extra cap this Gameweek. */
  max_transfers_this_event: number | null;
};

export type PlannerRecommendation = Recommendation & {
  gameweek_optimum?: Plan | null;
  chip_advice?: ChipAdvice[];
};

export type PriceSuggestion = {
  player_id: number;
  purchase_price_units: number | null;
  selling_price_units: number | null;
  provenance: string;
};

export const ESTIMATE_PROVENANCE = "published_gameweek_price_estimate";

export const defaultSettings: PlannerSettings = {
  horizon_events: 6,
  max_additional_hit_points: 0,
  locked_player_ids: [],
  excluded_player_ids: [],
  chip_policy: "none",
  solver_time_limit_seconds: 15,
  max_transfers_this_event: null,
};
