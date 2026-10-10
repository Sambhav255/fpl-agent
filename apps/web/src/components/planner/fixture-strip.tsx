"use client";

import type { Player } from "../../lib/api/client";
import type { Fixture } from "./logic";
import { upcomingFixtures } from "./view-model";

export function FixtureStrip({
  playerIds,
  players,
  fixtures,
  fromEvent,
}: {
  playerIds: number[];
  players: Map<number, Player>;
  fixtures: Fixture[];
  fromEvent: number;
}) {
  return (
    <section className="panel">
      <p className="eyebrow">THE NEXT WEEKS</p>
      <h2>Fixture strip</h2>
      <p className="muted">
        Difficulty is the official number. Colour repeats that number and is not the only signal.
      </p>
      {!fixtures.length ? (
        <p>Fixtures unavailable until a forecast run includes them.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <caption>Upcoming fixtures for the players on the pitch</caption>
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">Next fixtures</th>
              </tr>
            </thead>
            <tbody>
              {playerIds.map((id) => {
                const player = players.get(id);
                const chips = player ? upcomingFixtures(player.club, fixtures, fromEvent, 5) : [];
                return (
                  <tr key={id}>
                    <th scope="row">{player?.name || id}</th>
                    <td>
                      {chips.length
                        ? chips.map((chip) => (
                            <span
                              className="fdr"
                              data-difficulty={String(Math.min(5, Math.max(1, chip.difficulty)))}
                              key={`${id}-${chip.event}`}
                              aria-label={`Gameweek ${chip.event}, ${chip.home ? "home" : "away"} versus club ${chip.opponent}, fixture difficulty ${chip.difficulty}`}
                            >
                              <b>GW{chip.event}</b>
                              {chip.home ? "H" : "A"} {chip.opponent}
                              <i>{chip.difficulty}</i>
                            </span>
                          ))
                        : "No fixture"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
