"""Optional network check using an explicitly supplied public team ID.
Preserves saved corrections; imports only if no local state exists.
"""
import argparse
import urllib.error
from smoke import request, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-id", required=True, type=int)
    team_id = parser.parse_args().team_id
    if team_id <= 0:
        raise ValueError("positive public team ID required")
    try:
        state = request(f"/teams/{team_id}/state")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        state = request("/teams/import", {"team_id": team_id})
    assert state["team_id"] == team_id and state["data_mode"] == "live"
    assert len(state["picks"]) == 15 and state["public_source_event"] is not None
    run = result(request("/projections/runs", {"team_id": team_id, "horizon_events": 2}))
    body = {"team_id": team_id, "expected_state_version": state["state_version"],
            "projection_run_id": run["projection_run_id"], "analysis_mode": "lineup",
            "settings": {"horizon_events": 2, "solver_time_limit_seconds": 5}}
    rec = result(request("/recommendations", body))
    keep = rec["baseline_plan"]
    assert len(keep["lineup"]["starters"]) == 11 and not rec["alternatives"]
    if state["bank_units"] is None:
        body["analysis_mode"] = "transfers"
        try:
            request("/recommendations", body)
        except urllib.error.HTTPError as error:
            assert error.code == 422
        else:
            raise AssertionError("unknown bank allowed transfers")
    saved = request("/plans", {"recommendation_id": rec["recommendation_id"], "plan_id": keep["plan_id"]})
    restored = request("/plans/" + saved["plan_id"])
    assert restored["team_id"] == team_id and not restored["stale_reasons"]
    assert request(f"/teams/{team_id}/state") == state
    print(f"PASS public team {team_id}: GW{state['public_source_event']} picks, live baseline, legal lineup, persisted plan; financial state preserved")


if __name__ == "__main__":
    main()
