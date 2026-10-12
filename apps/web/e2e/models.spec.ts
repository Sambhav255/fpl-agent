import { test, expect } from "@playwright/test";

test("model registry loads independently of manager state", async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  const registryLoaded = page.waitForResponse(
    (response) => response.url().includes("/api/v1/models") && response.ok(),
  );
  await page.goto("/models");
  await registryLoaded;
  await expect(page.getByRole("heading", { name: "Model registry" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Baseline", exact: true })).toBeVisible();
  await expect(page.getByText(/Used for predictions/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Temporal Fusion Transformer" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Multilead TFT (research)", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Mean ensemble (research)", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh model status" })).toBeEnabled();
  const registry = await (await page.request.get("/api/v1/models")).json();
  for (const model of registry.models) {
    if (!model.artifacts) continue;
    expect(model.active).toBe(false);
    expect(model.strict_release_eligible).toBe(false);
    for (const artifact of model.artifacts) {
      await expect(
        page.getByText(`${artifact.artifact_id}: ${artifact.status.replaceAll("_", " ")}`, {
          exact: true,
        }),
      ).toBeVisible();
    }
  }
  await expect(page.getByRole("heading", { name: "Strategy research" })).toBeVisible();
  const strategy = await (await page.request.get("/api/v1/strategy/status")).json();
  expect(strategy.champion).toBe("numerical_planner");
  expect(strategy.automatic_promotion).toBe(false);
  for (const policy of strategy.policies) {
    expect(policy.active).toBe(false);
    await expect(page.getByText(policy.artifact_id, { exact: false })).toBeVisible();
  }
});

test("configured personal team loads without reimporting", async ({ page }) => {
  test.skip(!process.env.FPL_LIVE_TEAM_ID, "Personal local configuration required");
  await page.addInitScript(() => localStorage.clear());
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") requests.push(request.url());
  });
  const stateLoaded = page.waitForResponse(
    (response) =>
      response.url().includes(`/teams/${process.env.FPL_LIVE_TEAM_ID}/state`) && response.ok(),
  );
  await page.goto("/planner");
  await stateLoaded;
  await expect(page.getByText(new RegExp(`Team ${process.env.FPL_LIVE_TEAM_ID}\\b`))).toBeVisible();
  expect(requests.some((url) => url.endsWith("/teams/import"))).toBe(false);
});

test("advanced shadows require reviewed current inputs and retain baseline", async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await page.goto("/models");
  await expect(page.getByRole("heading", { name: "Advanced shadow forecasts" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run shadow forecast", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Shadow team ID", { exact: true }).fill("987654321");
  await page.getByRole("button", { name: "Load reviewed shadow models" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: /does not exist|not found/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run shadow forecast", exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole("heading", { name: "Baseline", exact: true })).toBeVisible();
  await expect(page.getByText("Used for predictions", { exact: false })).toHaveCount(1);
});

test("experimental model selection blocks stale personal state without changing it", async ({
  page,
}) => {
  test.skip(!process.env.FPL_LIVE_TEAM_ID, "Personal local configuration required");
  await page.addInitScript(
    (id) => localStorage.setItem("touchline.team", id),
    process.env.FPL_LIVE_TEAM_ID!,
  );
  const before = await (
    await page.request.get(`/api/v1/teams/${process.env.FPL_LIVE_TEAM_ID}/state`)
  ).json();
  const readiness = await page.request.get(
    `/api/v1/teams/${process.env.FPL_LIVE_TEAM_ID}/readiness`,
  );
  test.skip(readiness.status() !== 409, "This check specifically requires stale live state");
  const posts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request.url());
  });
  await page.goto("/models");
  const button = page.getByRole("button", { name: "Run experimental forecast", exact: true });
  await expect(button).toBeEnabled();
  await button.click();
  await expect(
    page.getByRole("alert").filter({ hasText: /stale|gameweek changed/i }),
  ).toBeVisible();
  expect(
    posts.some((url) => url.endsWith("/projections/runs") || url.endsWith("/teams/import")),
  ).toBe(false);
  const after = await (
    await page.request.get(`/api/v1/teams/${process.env.FPL_LIVE_TEAM_ID}/state`)
  ).json();
  expect(after).toEqual(before);
  await expect(page.getByRole("heading", { name: "Baseline", exact: true })).toBeVisible();
});
