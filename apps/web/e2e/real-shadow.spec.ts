import { test, expect } from "@playwright/test";

test("real retained football → immutable release → queued shadow → displayed means → analysis", async ({
  page,
}) => {
  const team = process.env.REAL_SHADOW_TEAM_ID;
  test.skip(
    !team,
    "Requires an isolated real-football release and hypothetical research portfolio",
  );
  test.setTimeout(240000);
  const state = await (await page.request.get(`/api/v1/teams/${team}/state`)).json();
  expect(state.warnings.join(" ")).toContain("Hypothetical research portfolio");
  const before = JSON.stringify(state);
  await page.goto("/models");
  await page.getByLabel("Shadow team ID", { exact: true }).fill(team!);
  const loaded = page.waitForResponse(
    (response) => response.url().includes("/api/v1/projections/bundles?") && response.ok(),
  );
  await page.getByRole("button", { name: "Load reviewed shadow models" }).click();
  const bundles = await (await loaded).json();
  expect(bundles.bundles.map((bundle: { provider: string }) => bundle.provider)).toEqual(
    expect.arrayContaining(["football_catboost", "ensemble"]),
  );
  const choice = page.getByRole("combobox", { name: "Reviewed shadow model", exact: true });
  await expect(choice.locator("option").filter({ hasText: "football_catboost" })).toHaveCount(1);
  const footballId = await choice
    .locator("option")
    .filter({ hasText: "football_catboost" })
    .getAttribute("value");
  await choice.selectOption(footballId!);
  await page.getByRole("button", { name: "Run shadow forecast", exact: true }).click();
  await expect(page.getByText(/Shadow completed: football_catboost/)).toBeVisible({
    timeout: 180000,
  });
  await expect(
    page
      .getByRole("table")
      .filter({ has: page.getByText("Unconditional fixture means; no default promotion") }),
  ).toBeVisible();
  await expect(page.getByText(/Run reference: football_catboost-/)).toBeVisible();
  const ensembleId = await choice
    .locator("option")
    .filter({ hasText: "ensemble" })
    .getAttribute("value");
  await choice.selectOption(ensembleId!);
  const completedJob = page.waitForResponse(async (response) => {
    if (!response.url().includes("/api/v1/jobs/") || !response.ok()) return false;
    const body = await response.json();
    return body.status === "succeeded" && body.result?.model_family === "ensemble";
  });
  await page.getByRole("button", { name: "Run shadow forecast", exact: true }).click();
  const run = (await (await completedJob).json()).result;
  await expect(page.getByText(/Shadow completed: ensemble/)).toBeVisible();
  expect(run.model_status).toBe("experimental");
  expect(run.projections.length).toBeGreaterThan(600);
  const response = await page.request.post("/api/v1/recommendations", {
    data: {
      team_id: Number(team),
      expected_state_version: state.state_version,
      projection_run_id: run.projection_run_id,
      settings: { horizon_events: 1, max_transfers_this_event: 1, solver_time_limit_seconds: 3 },
    },
  });
  expect(response.status()).toBe(202);
  const queued = await response.json();
  let result;
  for (let attempts = 0; attempts < 90; attempts++) {
    const job = await (await page.request.get(`/api/v1/jobs/${queued.job_id}`)).json();
    expect(["failed", "cancelled"]).not.toContain(job.status);
    if (job.status === "succeeded") {
      result = job.result;
      break;
    }
    await page.waitForTimeout(500);
  }
  expect(result).toBeTruthy();
  expect(result.baseline_plan.lineup.starters).toHaveLength(11);
  expect(result.baseline_plan.net_points).toBeCloseTo(
    result.baseline_plan.gross_points - result.baseline_plan.total_hits,
  );
  const frozen = await page.request.post("/api/v1/learning/decisions", {
    data: {
      recommendation_id: result.recommendation_id,
      idempotency_key: `real-shadow-${run.projection_run_id}`,
    },
  });
  expect(frozen.ok()).toBeTruthy();
  const journal = await frozen.json();
  expect(journal.evidence_mode).toBe("prospective_shadow");
  expect(journal.execution_status).toBe("execution_unknown");
  const paper = await page.request.post(
    `/api/v1/learning/decisions/${journal.decision_id}/actions`,
    {
      data: {
        idempotency_key: `paper-${run.projection_run_id}`,
        expected_sequence: journal.action_history.length,
        execution_status: "execution_unknown",
        paper_portfolio_action_id: journal.recommended_action_id,
      },
    },
  );
  expect(paper.ok()).toBeTruthy();
  expect(JSON.stringify(await (await page.request.get(`/api/v1/teams/${team}/state`)).json())).toBe(
    before,
  );
});
