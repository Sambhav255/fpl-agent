"""Live-process offline-demo integration check. API + worker must already run."""

import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def request(path, body=None, method=None):
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method or ("GET" if body is None else "POST"),
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def result(job):
    for _ in range(180):
        row = request("/jobs/" + job["job_id"])
        if row["status"] == "succeeded":
            return row["result"]
        if row["status"] in {"failed", "cancelled"}:
            raise AssertionError(row)
        time.sleep(0.5)
    raise AssertionError("Worker failed to complete within 90 seconds")


def main():
    assert request("/health")
    state = request("/demo", {})
    assert state["data_mode"] == "demo" and len(state["picks"]) == 15
    run = result(request("/projections/runs", {"team_id": state["team_id"], "horizon_events": 2}))
    assert run["data_mode"] == "demo" and run["projections"]
    analysis_body = {
        "team_id": state["team_id"],
        "expected_state_version": state["state_version"],
        "projection_run_id": run["projection_run_id"],
        "settings": {"horizon_events": 2, "solver_time_limit_seconds": 5},
    }
    rec = result(request("/recommendations", analysis_body))
    keep = rec["baseline_plan"]
    assert len(keep["lineup"]["starters"]) == 11
    assert keep["net_points"] == keep["gross_points"] - keep["total_hits"]
    saved = request(
        "/plans", {"recommendation_id": rec["recommendation_id"], "plan_id": keep["plan_id"]}
    )
    assert saved
    reloaded = request("/plans/" + keep["plan_id"])
    assert reloaded
    corrected = dict(state)
    corrected["bank_units"] = None
    changed = request(
        "/teams/" + str(state["team_id"]) + "/state",
        {"expected_version": state["state_version"], "state": corrected},
        "PATCH",
    )
    try:
        request("/recommendations", analysis_body)
    except urllib.error.HTTPError as error:
        assert error.code == 409
    else:
        raise AssertionError("Stale state was accepted")
    assert changed["bank_units"] is None
    analysis_body["expected_state_version"] = changed["state_version"]
    try:
        request("/recommendations", analysis_body)
    except urllib.error.HTTPError as error:
        assert error.code == 422
    else:
        raise AssertionError("Transfer request with unknown bank accepted")
    analysis_body["analysis_mode"] = "lineup"
    lineup_only = result(request("/recommendations", analysis_body))
    assert not lineup_only["alternatives"]
    assert lineup_only["baseline_plan"]["solver"]["status"] == "lineup_only"
    assert any("blocked" in w.lower() for w in lineup_only["warnings"])
    stale_plan = request("/plans/" + keep["plan_id"])
    assert stale_plan["stale_reasons"]
    print(
        "PASS actual API + worker: demo, projection, recommendation, save/reload, state edit, stale rejection, unknown finances lineup-only, saved-plan staleness"
    )


if __name__ == "__main__":
    main()
