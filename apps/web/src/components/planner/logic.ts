import type { Pick as SquadPick, Plan } from "../../lib/api/client";
import type { components } from "../../lib/api/schema";
import { ESTIMATE_PROVENANCE, type PlannerSettings, type PriceSuggestion } from "./types";

export type Fixture = components["schemas"]["Fixture"];

const CONFIRMED_SALE = new Set(["user_confirmed", "private_verified", "demo", "synthetic"]);

export type SalePick = {
  purchase_price_units?: number | null;
  selling_price_units?: number | null;
  selling_price_provenance?: string | null;
};

export function remainingFreeTransfers(
  free: number | null | undefined,
  made: number | null | undefined,
): number | null {
  if (free == null || made == null) return null;
  if (!Number.isInteger(free) || !Number.isInteger(made)) return null;
  return Math.max(0, free - made);
}

/** Stepper count is 0 through the remaining free transfers. One allowed hit adds one move and a 4-point budget. */
export function transferSettings(input: {
  count: number;
  allowHit: boolean;
  free: number | null | undefined;
  made: number | null | undefined;
}): Pick<PlannerSettings, "max_transfers_this_event" | "max_additional_hit_points"> {
  const remaining = remainingFreeTransfers(input.free, input.made);
  if (remaining == null) {
    return { max_transfers_this_event: null, max_additional_hit_points: input.allowHit ? 4 : 0 };
  }
  const count = Math.min(remaining, Math.max(0, Math.trunc(input.count)));
  return {
    max_transfers_this_event: count + (input.allowHit ? 1 : 0),
    max_additional_hit_points: input.allowHit ? 4 : 0,
  };
}

export function countFromSettings(
  maxTransfers: number | null | undefined,
  remaining: number | null,
  allowHit: boolean,
): number | null {
  if (remaining == null) return null;
  if (maxTransfers == null) return remaining;
  return Math.min(remaining, Math.max(0, maxTransfers - (allowHit ? 1 : 0)));
}

export function pickSaleConfirmed(pick: SalePick): boolean {
  if (pick.selling_price_provenance === ESTIMATE_PROVENANCE) return false;
  if (pick.selling_price_units != null && CONFIRMED_SALE.has(pick.selling_price_provenance || ""))
    return true;
  return pick.purchase_price_units != null;
}

export function transferSearchAllowed(input: {
  bank: number | null | undefined;
  free: number | null | undefined;
  made: number | null | undefined;
  hits: number | null | undefined;
  picks: SalePick[];
}): boolean {
  if (input.bank == null || input.free == null || input.made == null || input.hits == null)
    return false;
  return input.picks.length > 0 && input.picks.every(pickSaleConfirmed);
}

export function transferBlockReason(input: {
  bank: number | null | undefined;
  free: number | null | undefined;
  made: number | null | undefined;
  hits: number | null | undefined;
  picks: SalePick[];
}): string | null {
  if (input.bank == null || input.free == null || input.made == null || input.hits == null) {
    return "Bank, free transfers, or hit cost is unknown. Transfer analysis is off.";
  }
  if (!input.picks.every(pickSaleConfirmed)) {
    return "Accept selling prices before transfer analysis. Transfer analysis is off.";
  }
  return null;
}

export type PriceDecision = {
  player_id: number;
  units: number | null;
  kind: "purchase" | "sell";
  rejected: boolean;
};

/** Blank rows stay as they are. Rejected rows return to unknown. An estimate is not saved here. */
export function applyAcceptedPrices(picks: SquadPick[], decisions: PriceDecision[]): SquadPick[] {
  const byId = new Map(decisions.map((decision) => [decision.player_id, decision]));
  return picks.map((pick) => {
    const decision = byId.get(pick.player_id);
    if (!decision) return pick;
    if (decision.rejected) {
      return {
        ...pick,
        purchase_price_units: null,
        selling_price_units: null,
        selling_price_market_units: null,
        selling_price_provenance: "unknown",
        confirmed_at: null,
      };
    }
    if (decision.units == null) return pick;
    if (decision.kind === "purchase") {
      return {
        ...pick,
        purchase_price_units: decision.units,
        selling_price_provenance:
          pick.selling_price_provenance === ESTIMATE_PROVENANCE
            ? "user_confirmed"
            : pick.selling_price_provenance,
      };
    }
    return {
      ...pick,
      selling_price_units: decision.units,
      selling_price_provenance: "user_confirmed",
      confirmed_at: new Date().toISOString(),
    };
  });
}

export function withSellMarket(
  picks: SquadPick[],
  marketUnits: (playerId: number) => number | null,
): SquadPick[] {
  return picks.map((pick) => {
    if (pick.selling_price_provenance !== "user_confirmed" || pick.selling_price_units == null)
      return pick;
    return { ...pick, selling_price_market_units: marketUnits(pick.player_id) };
  });
}

export function parseSuggestions(payload: unknown): PriceSuggestion[] {
  const rows = Array.isArray(payload)
    ? payload
    : payload &&
        typeof payload === "object" &&
        Array.isArray((payload as { suggestions?: unknown }).suggestions)
      ? (payload as { suggestions: unknown[] }).suggestions
      : [];
  return rows.flatMap((row) => {
    if (!row || typeof row !== "object") return [];
    const record = row as Record<string, unknown>;
    if (typeof record.player_id !== "number") return [];
    return [
      {
        player_id: record.player_id,
        purchase_price_units:
          typeof record.purchase_price_units === "number" ? record.purchase_price_units : null,
        selling_price_units:
          typeof record.selling_price_units === "number" ? record.selling_price_units : null,
        provenance: typeof record.provenance === "string" ? record.provenance : ESTIMATE_PROVENANCE,
      },
    ];
  });
}

export function formatDeadline(value: unknown, timeZone?: string): string {
  if (typeof value !== "string" || Number.isNaN(Date.parse(value))) return "Unknown";
  const parts = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone,
  }).formatToParts(new Date(value));
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? "";
  const clock = `${part("hour")}:${part("minute")}`;
  if (!part("weekday") || !part("day") || !part("month") || clock === ":") return "Unknown";
  return `${part("weekday")} ${part("day")} ${part("month")}, ${clock}`;
}

export function deadlineValue(status: Record<string, unknown>): unknown {
  if (typeof status.deadline_time === "string") return status.deadline_time;
  return status.deadline;
}

export function weekNet(plan: Plan | null | undefined, index = 0): number | null {
  const value = plan?.weeks?.[index]?.net_points;
  return typeof value === "number" ? value : null;
}

export function planGains(plan: Plan, keep: Plan): { thisWeek: number | null; horizon: number } {
  const current = weekNet(plan);
  const baseline = weekNet(keep);
  return {
    thisWeek: current != null && baseline != null ? current - baseline : null,
    horizon: plan.delta_to_baseline,
  };
}
