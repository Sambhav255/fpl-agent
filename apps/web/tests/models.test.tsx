import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import ModelStatus from "../src/components/model-status";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("independent model registry", () => {
  it("loads without any imported team and distinguishes diagnostic from active", async () => {
    localStorage.clear();
    const fetcher = vi.fn().mockImplementation(async (path: string) => ({
      ok: true,
      json: async () => ({
        ...(path.endsWith("/data/collections") ? { collections: [] } : {}),
        models: [
          { model_family: "baseline", status: "active", reason: "Approximate baseline" },
          {
            model_family: "catboost",
            status: "evaluated",
            active: false,
            evaluation_kind: "retrospective_unverified",
            reason: ["Unverified timing"],
          },
        ],
      }),
    }));
    vi.stubGlobal("fetch", fetcher);
    render(<ModelStatus />);
    expect(await screen.findByText("CatBoost")).toBeVisible();
    expect(screen.getByText(/Retrospective diagnostic only/)).toBeVisible();
    expect(screen.getByText(/Inactive for predictions/)).toBeVisible();
    expect(fetcher.mock.calls.some(([path]) => path === "/api/v1/models")).toBe(true);
    expect(fetcher.mock.calls.some(([path]) => String(path).includes("/teams/import"))).toBe(false);
  });
  it("shows API errors rather than requesting a team import", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Registry unavailable")));
    render(<ModelStatus />);
    expect(await screen.findByText("Registry unavailable")).toBeVisible();
    expect(screen.getByRole("button", { name: "Refresh model status" })).toBeEnabled();
  });
});
