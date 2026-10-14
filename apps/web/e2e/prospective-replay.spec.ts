import { test, expect } from "@playwright/test";

test("sealed real baseline paper journal is displayed and future outcomes stay pending", async ({
  page,
}) => {
  const team = process.env.PROSPECTIVE_REPLAY_TEAM_ID;
  const decision = process.env.PROSPECTIVE_REPLAY_DECISION_ID;
  test.skip(
    !team || !decision,
    "Requires a fresh sealed journal in an isolated research portfolio",
  );
  test.setTimeout(120000);
  const stateResponse = await page.request.get(`/api/v1/teams/${team}/state`);
  expect(stateResponse.ok()).toBeTruthy();
  const state = await stateResponse.json();
  expect(state.warnings.join(" ")).toContain("Hypothetical research portfolio");
  const before = JSON.stringify(state);
  const frozen = await (await page.request.get(`/api/v1/learning/decisions/${decision}`)).json();
  expect(frozen.execution_status).toBe("execution_unknown");
  expect(frozen.forecast.projection_run_id).toMatch(/^baseline-replay-/);
  expect(frozen.forecast.horizon_events).toBe(6);
  expect(frozen.forecast.projections.length).toBeGreaterThan(3000);
  expect(Date.now()).toBeLessThan(Date.parse(frozen.deadline));
  const backup = await (await page.request.get("/api/v1/backup")).json();
  const seals = backup.learning_replay_seals.filter(
    (row: { decision_id: string }) => row.decision_id === decision,
  );
  expect(seals).toHaveLength(3);
  for (const seal of seals) {
    expect(seal.manifest_sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(Date.parse(seal.sealed_at)).toBeGreaterThanOrEqual(Date.parse(frozen.decision_origin));
    expect(Date.parse(seal.sealed_at)).toBeLessThan(Date.parse(frozen.deadline));
  }
  await page.addInitScript((id) => localStorage.setItem("touchline.team", id), team!);
  await page.goto("/history");
  const card = page.locator(`[data-decision-id="${decision}"]`);
  await expect(card).toBeVisible({ timeout: 30000 });
  await expect(card.getByText(/Execution status:.*unknown/i)).toBeVisible();
  const pending = await page.request.post(`/api/v1/learning/decisions/${decision}/outcomes`, {
    data: {},
  });
  expect(pending.status()).toBe(202);
  expect((await pending.json()).status).toBe("pending");
  const reread = await (await page.request.get(`/api/v1/learning/decisions/${decision}`)).json();
  expect(reread.outcome_revisions).toHaveLength(0);
  expect(reread.execution_status).toBe("execution_unknown");
  expect(JSON.stringify(await (await page.request.get(`/api/v1/teams/${team}/state`)).json())).toBe(
    before,
  );
});
