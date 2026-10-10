"use client";

import { money, type Pick, type Player } from "../../lib/api/client";
import type { Fixture } from "./logic";
import { availabilityText, positionName, positionShort, thisEventFixture } from "./view-model";

type Points = Map<number, { points: number }>;

export function LineupPitch({
  title,
  event,
  starters,
  bench,
  captain,
  vice,
  players,
  picks,
  points,
  fixtures,
}: {
  title: string;
  event: number;
  starters: number[];
  bench: number[];
  captain?: number;
  vice?: number;
  players: Map<number, Player>;
  picks: Pick[];
  points: Points;
  fixtures: Fixture[];
}) {
  const renderPlayer = (id: number, benched = false) => {
    const player = players.get(id);
    const role = id === captain ? "Captain" : id === vice ? "Vice" : benched ? "Bench" : "Starter";
    const fixture = player ? thisEventFixture(player.club, fixtures, event) : null;
    const opponent = fixture
      ? `${fixture.home ? "Home" : "Away"} v ${fixture.opponent} · difficulty ${fixture.difficulty}`
      : "Opponent unknown";
    return (
      <div className={`pitch-player ${benched ? "benched" : ""}`} key={id}>
        <div className="shirt" aria-hidden="true">
          {positionShort[player?.position || 0]}
          {id === captain ? <b>C</b> : id === vice ? <b>V</b> : null}
        </div>
        <strong>{player?.name || `Player ${id}`}</strong>
        <span>
          {positionShort[player?.position || 0]} · {role}
        </span>
        <span>{points.has(id) ? `${points.get(id)!.points.toFixed(1)} xP` : "xP unavailable"}</span>
        <span>{opponent}</span>
        <span>
          {money(player?.market_price_units)} · {availabilityText(player)}
        </span>
      </div>
    );
  };
  const tablePicks = [...starters, ...bench].map((id, index) => {
    const existing = picks.find((pick) => pick.player_id === id);
    return {
      player_id: id,
      position: index + 1,
      is_captain: id === captain,
      is_vice_captain: id === vice,
      selling_price_units: existing?.selling_price_units,
      purchase_price_units: existing?.purchase_price_units,
      selling_price_market_units: existing?.selling_price_market_units,
      selling_price_provenance: existing?.selling_price_provenance || "unknown",
      confirmed_at: existing?.confirmed_at,
      acquisition_id: existing?.acquisition_id,
    } satisfies Pick;
  });
  return (
    <section className="panel squad-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">THE MATCHDAY PICTURE</p>
          <h2>{title}</h2>
        </div>
        <span className="tag">GW {event}</span>
      </div>
      <div
        className="pitch"
        role="img"
        aria-label="Football pitch lineup; full player details in the squad table below"
      >
        <div className="pitch-circle" />
        {[1, 2, 3, 4].map((position) => (
          <div className="pitch-row" key={position}>
            {starters
              .filter((id) => players.get(id)?.position === position)
              .map((id) => renderPlayer(id))}
          </div>
        ))}
      </div>
      <div className="bench">
        <span className="eyebrow">BENCH · PRIORITY ORDER</span>
        <div className="bench-row">{bench.map((id) => renderPlayer(id, true))}</div>
      </div>
      <SquadTable
        picks={tablePicks}
        players={players}
        points={points}
        fixtures={fixtures}
        event={event}
      />
    </section>
  );
}

function SquadTable({
  picks,
  players,
  points,
  fixtures,
  event,
}: {
  picks: Pick[];
  players: Map<number, Player>;
  points: Points;
  fixtures: Fixture[];
  event: number;
}) {
  return (
    <details className="squad-table" open>
      <summary>Accessible squad table</summary>
      <div className="table-scroll">
        <table>
          <caption>
            Same squad as the pitch. Slots 1–11 start. Slots 12–15 are bench priority.
          </caption>
          <thead>
            <tr>
              <th scope="col">Slot</th>
              <th scope="col">Player</th>
              <th scope="col">Position</th>
              <th scope="col">Role</th>
              <th scope="col">Price</th>
              <th scope="col">Opponent</th>
              <th scope="col">Availability</th>
              <th scope="col">GW xP</th>
            </tr>
          </thead>
          <tbody>
            {[...picks]
              .sort((a, b) => a.position - b.position)
              .map((pick) => {
                const player = players.get(pick.player_id);
                const fixture = player ? thisEventFixture(player.club, fixtures, event) : null;
                const role = pick.is_captain
                  ? "Captain"
                  : pick.is_vice_captain
                    ? "Vice"
                    : pick.position <= 11
                      ? "Starter"
                      : "Bench";
                return (
                  <tr key={pick.player_id}>
                    <td>{pick.position <= 11 ? pick.position : `Bench ${pick.position - 11}`}</td>
                    <th scope="row">{player?.name || pick.player_id}</th>
                    <td>{positionName[player?.position || 0] || "Unknown"}</td>
                    <td>{role}</td>
                    <td>{money(player?.market_price_units)}</td>
                    <td>
                      {fixture
                        ? `${fixture.home ? "Home" : "Away"} v ${fixture.opponent}`
                        : "Unknown"}
                    </td>
                    <td>{availabilityText(player)}</td>
                    <td>{points.get(pick.player_id)?.points.toFixed(1) ?? "Unavailable"}</td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
