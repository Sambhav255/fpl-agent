import type { Plan, Player, Recommendation } from "../../lib/api/client";
import type { Fixture } from "./logic";
import type { ChipAdvice, ChipAdviceStatus, PlannerRecommendation } from "./types";

const CHIP_STATUSES: ChipAdviceStatus[] = [
  "used",
  "unavailable",
  "save",
  "play_this_week",
  "not_evaluated",
];

export type TransferPair = {
  out: number;
  in: number;
  sale: number | null;
  purchase: number | null;
  bank: number | null;
  event: number | null;
};

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function transferPairs(plan: Plan | null | undefined, event?: number): TransferPair[] {
  if (!plan) return [];
  const week =
    event == null
      ? plan.weeks?.[0]
      : (plan.weeks?.find((item) => item.event === event) ?? plan.weeks?.[0]);
  const actions = Array.isArray(week?.actions) ? week.actions : (plan.actions ?? []);
  return actions.flatMap((action) => {
    if (!action || typeof action !== "object") return [];
    const row = action as Record<string, unknown>;
    const out = asNumber(row.out ?? row.out_player_id ?? row.player_out);
    const incoming = asNumber(row.in ?? row.in_player_id ?? row.player_in);
    if (out == null || incoming == null) return [];
    return [
      {
        out,
        in: incoming,
        sale: asNumber(row.sale_units),
        purchase: asNumber(row.purchase_units),
        bank: asNumber(row.bank_units),
        event: asNumber(row.event),
      },
    ];
  });
}

export function gameweekOptimum(recommendation: Recommendation | null): Plan | null {
  if (!recommendation) return null;
  const value = (recommendation as PlannerRecommendation).gameweek_optimum;
  return value ?? null;
}

export function readChipAdvice(recommendation: Recommendation | null): ChipAdvice[] {
  const value = (recommendation as PlannerRecommendation | null)?.chip_advice;
  if (!Array.isArray(value)) return [];
  return value.flatMap((row) => {
    if (!row || typeof row.chip !== "string" || !CHIP_STATUSES.includes(row.status)) return [];
    return [
      {
        chip: row.chip,
        status: row.status,
        this_week_points: typeof row.this_week_points === "number" ? row.this_week_points : null,
        comparison_points: typeof row.comparison_points === "number" ? row.comparison_points : null,
        reason: typeof row.reason === "string" ? row.reason : "",
      },
    ];
  });
}

export function ids(value: unknown): number[] {
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === "number")
    : [];
}

export type FixtureChip = {
  event: number;
  opponent: number;
  home: boolean;
  difficulty: number;
};

export function upcomingFixtures(
  club: number,
  fixtures: Fixture[],
  fromEvent: number,
  count: number,
): FixtureChip[] {
  return fixtures
    .filter(
      (fixture) =>
        fixture.event != null &&
        fixture.event >= fromEvent &&
        (fixture.home_club === club || fixture.away_club === club),
    )
    .sort((a, b) => (a.event ?? 0) - (b.event ?? 0) || a.fixture_id - b.fixture_id)
    .slice(0, count)
    .map((fixture) => {
      const home = fixture.home_club === club;
      return {
        event: fixture.event ?? fromEvent,
        opponent: home ? fixture.away_club : fixture.home_club,
        home,
        difficulty: home ? fixture.home_difficulty : fixture.away_difficulty,
      };
    });
}

export function thisEventFixture(
  club: number,
  fixtures: Fixture[],
  event: number,
): FixtureChip | null {
  return (
    upcomingFixtures(club, fixtures, event, 8).find((fixture) => fixture.event === event) ?? null
  );
}

export function availabilityText(player: Player | undefined): string {
  if (!player) return "Unknown";
  const words: Record<string, string> = {
    a: "Available",
    d: "Doubtful",
    i: "Injured",
    s: "Suspended",
    u: "Unavailable",
  };
  const status = words[player.status] ?? player.status;
  if (player.availability == null) return `${status} · availability unknown`;
  return `${status} · ${Math.round(player.availability * 100)}%`;
}

export function formatSigned(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "Unknown";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}`;
}

export const positionName = ["", "Goalkeeper", "Defender", "Midfielder", "Forward"];
export const positionShort = ["", "GK", "DEF", "MID", "FWD"];

export function chipLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
