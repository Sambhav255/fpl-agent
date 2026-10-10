import { describe, expect, it, vi, afterEach } from "vitest";
import { api, ApiError, money, parseMoney, teamId, totals } from "../src/lib/api/client";
afterEach(() => vi.unstubAllGlobals());
describe("manager input boundaries", () => {
 it("keeps unknown finances distinct from zero and stores tenths", () => {expect(parseMoney("")).toBeNull(); expect(parseMoney("7.5")).toBe(75); expect(money(0)).toBe("£0.0m"); expect(money(null)).toBe("Unknown"); expect(() => parseMoney("7.55")).toThrow();});
 it("accepts only numeric IDs and official points URLs", () => {expect(teamId("123")).toBe(123); expect(teamId("https://fantasy.premierleague.com/entry/123/event/8/")).toBe(123); for(const value of ["0","https://evil.test/entry/123/event/8/","https://fantasy.premierleague.com.evil.test/entry/123/event/8/"]) expect(()=>teamId(value)).toThrow();});
 it("surfaces optimistic concurrency conflicts without overwriting", async () => {const fetcher=vi.fn().mockResolvedValue({ok:false,status:409,json:async()=>({code:"STATE_VERSION_CONFLICT",message:"Reload current state"})});vi.stubGlobal("fetch",fetcher);await expect(api("/teams/1/state",{expected_version:1,state:{}},"PATCH")).rejects.toBeInstanceOf(ApiError);expect(JSON.parse(fetcher.mock.calls[0][1].body).expected_version).toBe(1);});
 it("does not apply a second availability multiplier to points", () => {const run={projections:[{player_id:1,event:8,expected_points:3,expected_minutes:40,appearance_probability:.5},{player_id:1,event:8,expected_points:-1,expected_minutes:20,appearance_probability:.5}]} as Parameters<typeof totals>[0];expect(totals(run,8).get(1)).toEqual({points:2,minutes:60,fixtures:2});expect(totals(run,9).size).toBe(0);});
});
