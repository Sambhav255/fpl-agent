import pytest
from test_upgrade_optimisation import funding_fixture

from fpl_app.domain.rules import (
    MatchStats,
    OfficialEventPoints,
    score_lineup,
    score_match,
    score_official_lineup,
    select_lineup,
)


def test_official_total_adapter_matches_components_autosubs_and_captain_fallback():
    state, players, run = funding_fixture()
    lineup = select_lineup(state, players, run.projections, state.next_event)
    stats = {p.player_id: [MatchStats(minutes=90, goals=int(p.position == 3))] for p in players}
    captain = lineup["captain"]
    stats[captain] = [MatchStats()]
    goalkeeper = next(
        i for i in lineup["starters"] if next(p.position for p in players if p.player_id == i) == 1
    )
    stats[goalkeeper] = [MatchStats()]
    by_id = {p.player_id: p for p in players}
    totals = {
        i: OfficialEventPoints(
            sum(score_match(by_id[i].position, r) for r in rows),
            sum(r.minutes for r in rows),
            any(r.minutes > 0 for r in rows),
        )
        for i, rows in stats.items()
    }
    direct = score_lineup(lineup, state, players, stats)
    assert score_official_lineup(lineup, state, players, totals) == direct
    assert direct["effective_captain"] == lineup["vice_captain"]
    assert direct["substitutions"]
    for chip in ["bench_boost", "triple_captain"]:
        assert score_official_lineup(lineup, state, players, totals, chip) == score_lineup(
            lineup, state, players, stats, chip
        )
    totals.pop(captain)
    with pytest.raises(ValueError, match="coverage"):
        score_official_lineup(lineup, state, players, totals)
