export function movesUsedText(used: number, cap: number | null): string | null {
  if (cap == null) return null;
  if (used < cap) return `Used ${used} of ${cap} transfers this Gameweek.`;
  return `Used ${used} transfer${used === 1 ? "" : "s"} this Gameweek.`;
}
