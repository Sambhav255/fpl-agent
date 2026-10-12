import { test, expect } from "@playwright/test";

test("planner caps one and three and persisted weekly plan", async ({ page }) => {
  test.setTimeout(120000);
  const state = await (await page.request.post("/api/v1/demo", { data: {} })).json();
  state.free_transfers_at_event_start = 3;
  state.bank_units = 7;
  state.chips.bench_boost = false;
  state.chips.bench_boost_1 = false;
  const patched = await page.request.patch("/api/v1/teams/0/state", {
    data: { expected_version: state.state_version, state },
  });
  expect(patched.ok()).toBe(true);
  await page.addInitScript(() => localStorage.setItem("touchline.team", "0"));
  const workspaceLoaded = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/teams/0/readiness") && response.request().method() === "GET",
  );
  await page.goto("/planner");
  await workspaceLoaded;
  await expect(page.getByRole("heading", { name: "Transfers this Gameweek" })).toBeVisible();
  await page.getByLabel("Horizon (Gameweeks)", { exact: true }).fill("2");
  await page.getByLabel("Solver limit (seconds)", { exact: true }).fill("3");
  await page.getByRole("button", { name: "Fewer transfers" }).click();
  await page.getByRole("button", { name: "Fewer transfers" }).click();
  for (const cap of [1, 3]) {
    if (cap === 3) {
      await page.getByRole("button", { name: "More transfers" }).click();
      await page.getByRole("button", { name: "More transfers" }).click();
    }
    const responsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/recommendations") && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Run analysis" }).click();
    const response = await responsePromise;
    expect(response.ok()).toBe(true);
    expect(response.request().postDataJSON().settings.max_transfers_this_event).toBe(cap);
    await expect(page.getByRole("status").filter({ hasText: "Analysis ready" })).toBeVisible({
      timeout: 90000,
    });
    await expect(page.getByRole("heading", { name: "Optimum move" })).toBeVisible();
    await page.getByRole("button", { name: "Save this-week plan" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Plan saved" })).toBeVisible();
  }
  await expect(
    page.getByText("Bench Boost already used in this chip window.", { exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({
    path: `test-results/planner-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test("optional live manager facts enforce financial and freshness gates", async ({ page }) => {
  test.skip(!process.env.FPL_LIVE_TEAM_ID, "Explicit public team ID required");
  await page.addInitScript(
    (id) => localStorage.setItem("touchline.team", id),
    process.env.FPL_LIVE_TEAM_ID!,
  );
  await page.goto("/planner");
  await expect(page.getByText(new RegExp(`Team ${process.env.FPL_LIVE_TEAM_ID}\\b`))).toBeVisible();
  const response = await page.request.get(
    `/api/v1/teams/${process.env.FPL_LIVE_TEAM_ID}/readiness`,
  );
  const readiness = await response.json();
  if (response.status() === 409) {
    expect(readiness.message).toMatch(/stale|gameweek changed/i);
    await expect(page.getByRole("button", { name: "Run analysis" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Run lineup only" })).toBeDisabled();
    await expect(page.getByText(/snapshot|reconcil/i).first()).toBeVisible();
  } else {
    expect(response.ok()).toBe(true);
    if (!readiness.transfers_ready) {
      expect(readiness.missing_fields.length + readiness.errors.length).toBeGreaterThan(0);
      await expect(page.getByRole("button", { name: "Run analysis" })).toBeDisabled();
    } else {
      await expect(page.getByRole("button", { name: "Run analysis" })).toBeEnabled();
    }
    await expect(page.getByRole("button", { name: "Run lineup only" })).toBeEnabled();
  }
  await page.screenshot({
    path: `test-results/live-planner-${test.info().project.name}.png`,
    fullPage: true,
  });
});
