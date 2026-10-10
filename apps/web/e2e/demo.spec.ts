import { test, expect } from "@playwright/test";
import type { components } from "../src/lib/api/schema";
// Requires the local API and recoverable worker using an isolated demo DATA_DIR.
// There are no provider requests. Projects run serially because the synthetic team is persisted.
test("synthetic demo → replacement and financial corrections → validated plan → saved reload", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/");
  await page.getByRole("button", { name: "Explore synthetic demo" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Synthetic demo loaded" })).toBeVisible();
  await expect(page.getByText("SYNTHETIC DEMO", { exact: true })).toBeVisible();
  const settingsLoaded = page.waitForResponse(
    (response) => response.url().includes("/api/v1/models") && response.ok(),
  );
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await settingsLoaded;
  await expect(page.getByRole("heading", { name: "Manager corrections" })).toBeVisible();
  await page.getByLabel("Bank (£m)", { exact: true }).fill("3.3");
  await page.getByRole("button", { name: "Reload current state", exact: true }).click();
  await expect(page.getByLabel("Bank (£m)", { exact: true })).toHaveValue("10.0");
  const current = (await (
    await page.request.get("/api/v1/teams/0/state")
  ).json()) as components["schemas"]["ManagerState"];
  const catalog = (await (
    await page.request.get("/api/v1/players?data_mode=demo")
  ).json()) as components["schemas"]["PlayersResponse"];
  const first = catalog.players.find((p) => p.player_id === current.picks[0].player_id)!;
  const owned = new Set(current.picks.map((p) => p.player_id));
  const clubCounts = new Map<number, number>();
  for (const pick of current.picks) {
    const club = catalog.players.find((p) => p.player_id === pick.player_id)!.club;
    clubCounts.set(club, (clubCounts.get(club) || 0) + 1);
  }
  const replacement = catalog.players.find(
    (p) =>
      !owned.has(p.player_id) &&
      p.position === first.position &&
      (clubCounts.get(p.club) || 0) - (p.club === first.club ? 1 : 0) < 3,
  )!;
  expect(replacement).toBeTruthy();
  await page
    .getByLabel("Player in slot 1", { exact: true })
    .selectOption(String(replacement.player_id));
  await expect(page.getByLabel("Purchase price for slot 1", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Selling price for slot 1", { exact: true })).toHaveValue("");
  await page.getByLabel("Bank (£m)", { exact: true }).fill("1.55");
  await expect(page.getByRole("button", { name: "Save corrections" }).first()).toBeDisabled();
  await page.getByLabel("Bank (£m)", { exact: true }).fill("1.0");
  await page
    .getByLabel("Purchase price for slot 1", { exact: true })
    .fill((replacement.market_price_units / 10).toFixed(1));
  await page
    .getByLabel("Selling price for slot 1", { exact: true })
    .fill((replacement.market_price_units / 10).toFixed(1));
  await page.getByLabel("Free transfers at event start", { exact: true }).fill("2");
  await page.getByLabel("Transfers already made", { exact: true }).fill("1");
  await page.getByLabel("Already committed hit points", { exact: true }).fill("0");
  await page.getByLabel("Current chip status confirmed", { exact: true }).check();
  await page.getByRole("button", { name: "Save corrections" }).first().click();
  await expect(page.getByRole("status").filter({ hasText: "Corrections saved" })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Player in slot 1", { exact: true })).toHaveValue(
    String(replacement.player_id),
  );
  await expect(page.getByLabel("Bank (£m)", { exact: true })).toHaveValue("1.0");
  await page.getByRole("link", { name: "Planner", exact: true }).click();
  await page.getByLabel("Horizon (Gameweeks)", { exact: true }).fill("2");
  await page.getByLabel("Solver limit (seconds)", { exact: true }).fill("2");
  await page.getByRole("button", { name: "Run analysis" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Analysis ready" })).toBeVisible({
    timeout: 90000,
  });
  await expect(page.getByRole("heading", { name: "Suggested Keep lineup" })).toBeVisible();
  await expect(page.getByRole("table").first()).toBeVisible();
  await page.screenshot({
    path: `test-results/dashboard-${test.info().project.name}.png`,
    fullPage: true,
  });
  await page
    .locator(".plan-card")
    .first()
    .getByRole("button", { name: /^Save / })
    .click();
  await expect(page.getByRole("status").filter({ hasText: "Plan saved" })).toBeVisible();
  await page.getByRole("link", { name: "Players", exact: true }).click();
  await expect(page.getByText("BASELINE PROJECTIONS", { exact: true })).toBeVisible();
  await page.getByLabel("Search players", { exact: true }).fill(replacement.name);
  await expect(page.getByRole("rowheader", { name: replacement.name, exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Saved plans", exact: true }).click();
  await expect(page.locator(".plan-card")).not.toHaveCount(0);
  await page.reload();
  await expect(page.locator(".plan-card")).not.toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({
    path: `test-results/demo-${test.info().project.name}.png`,
    fullPage: true,
  });
});
test("invalid import is rejected locally with a useful error", async ({ page }) => {
  await page.route("**/api/v1/teams/*/state", (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ message: "No saved profile" }),
    }),
  );
  await page.goto("/settings");
  await page
    .getByLabel("Team ID or official Points page URL")
    .fill("https://evil.test/entry/1/event/8/");
  await page.getByRole("button", { name: "Import team", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "positive numeric team ID" })).toHaveText(
    /positive numeric team ID/,
  );
});

test("stale readiness conflict still permits latest catalogue corrections and reanalysis", async ({
  page,
}) => {
  test.setTimeout(120000);
  const old = (await (
    await page.request.post("/api/v1/demo", { data: {} })
  ).json()) as components["schemas"]["ManagerState"];
  const fresh = (await (
    await page.request.post("/api/v1/demo", { data: {} })
  ).json()) as components["schemas"]["ManagerState"];
  // Emulate the persisted pre-refresh state reads while retaining the real backend version.
  // /demo refreshes both source and state, so only stale reads are injected here.
  await page.route("**/api/v1/teams/0/state", async (route) => {
    if (route.request().method() === "GET")
      await route.fulfill({ json: { ...fresh, snapshot_id: old.snapshot_id } });
    else await route.continue();
  });
  await page.route("**/api/v1/teams/0/readiness", (route) =>
    route.fulfill({
      status: 409,
      json: { code: "STALE_INPUTS", message: "Manager snapshot stale" },
    }),
  );
  await page.goto("/settings");
  await page.evaluate(() => localStorage.setItem("touchline.team", "0"));
  await page.reload();
  await expect(page.getByRole("heading", { name: "Manager corrections" })).toBeVisible();
  await expect(
    page.getByText("Manager state uses an older snapshot.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByLabel("Player in slot 1", { exact: true })).toBeVisible();
  // Real PATCH reconciles against the latest /players snapshot.
  await page.unroute("**/api/v1/teams/0/state");
  await page.unroute("**/api/v1/teams/0/readiness");
  await page.getByRole("button", { name: "Save corrections" }).first().click();
  await expect(page.getByRole("status").filter({ hasText: "Corrections saved" })).toBeVisible();
  await expect(
    page.getByText("Manager state uses an older snapshot.", { exact: false }),
  ).not.toBeVisible();
  await page.getByRole("link", { name: "Planner", exact: true }).click();
  await page.getByLabel("Horizon (Gameweeks)").fill("1");
  await page.getByLabel("Solver limit (seconds)").fill("1");
  await page.getByRole("button", { name: "Run analysis" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Analysis ready" })).toBeVisible({
    timeout: 90000,
  });
});
