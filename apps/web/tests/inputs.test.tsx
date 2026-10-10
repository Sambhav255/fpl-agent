import React from "react";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MoneyInput, JsonInput } from "../src/components/dashboard";
afterEach(cleanup);
describe("correction editors",()=>{
 it("reports invalid price text and never commits it as valid money",()=>{const change=vi.fn();const validity=vi.fn();render(<MoneyInput label="Bank" value={10} onChange={change} onValidity={validity}/>);fireEvent.change(screen.getByLabelText("Bank"),{target:{value:"1.55"}});expect(change).not.toHaveBeenCalled();expect(validity).toHaveBeenLastCalledWith("Bank",true);expect(screen.getByLabelText("Bank")).toHaveAttribute("aria-invalid","true");fireEvent.change(screen.getByLabelText("Bank"),{target:{value:"0"}});expect(change).toHaveBeenLastCalledWith(0);expect(validity).toHaveBeenLastCalledWith("Bank",false);});
 it("clears a replaced player's price editor rather than carrying the previous purchase price",()=>{const change=vi.fn();const {rerender}=render(<MoneyInput key="player1" label="Purchase" value={75} onChange={change}/>);expect(screen.getByLabelText("Purchase")).toHaveValue("7.5");rerender(<MoneyInput key="player2" label="Purchase" value={null} onChange={change}/>);expect(screen.getByLabelText("Purchase")).toHaveValue("");});
 it("rejects malformed or nonarray restoration records",()=>{const change=vi.fn();const validity=vi.fn();render(<JsonInput label="Persistent squad" value={null} onChange={change} onValidity={validity}/>);fireEvent.change(screen.getByLabelText("Persistent squad"),{target:{value:'{"invalid":true}'}});expect(change).not.toHaveBeenCalled();expect(validity).toHaveBeenLastCalledWith("Persistent squad",true);fireEvent.change(screen.getByLabelText("Persistent squad"),{target:{value:"[]"}});expect(change).toHaveBeenLastCalledWith([]);expect(validity).toHaveBeenLastCalledWith("Persistent squad",false);});
});
