/** Local preference only; loading a profile never reimports or overwrites state. */
export function preferredTeamId(): string | null {
  const saved = localStorage.getItem("touchline.team");
  if (saved !== null && /^\d+$/.test(saved)) return saved;
  const configured = process.env.NEXT_PUBLIC_DEFAULT_TEAM_ID?.trim();
  return configured && /^[1-9]\d*$/.test(configured) ? configured : null;
}
