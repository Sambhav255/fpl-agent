"use client";

import { useEffect, useState } from "react";
import { parseMoney } from "../lib/api/client";

export function MoneyInput({label,value,onChange,hidden=false,onValidity}:{label:string;value:number|null|undefined;onChange:(v:number|null)=>void;hidden?:boolean;onValidity?:(name:string,invalid:boolean)=>void}){
  const [text,setText]=useState(value==null?"":(value/10).toFixed(1));
  const [invalid,setInvalid]=useState(false);
  useEffect(()=>()=>onValidity?.(label,false),[onValidity,label]);
  // Parent keys reset local editing text on a new state version or player replacement.
  return <label className={hidden?"money-label":""}>{!hidden&&label}<input aria-label={label} inputMode="decimal" value={text} aria-invalid={invalid} placeholder="Unknown" onChange={e=>{setText(e.target.value);try{const units=parseMoney(e.target.value);setInvalid(false);onValidity?.(label,false);e.target.setCustomValidity("");onChange(units);}catch{setInvalid(true);onValidity?.(label,true);e.target.setCustomValidity("Use a nonnegative price with one decimal place.");}}}/>{invalid&&<small role="alert">Use 0.1m increments</small>}</label>;
}
export function JsonInput({label,value,onChange,onValidity}:{label:string;value:unknown;onChange:(value:unknown)=>void;onValidity?:(name:string,invalid:boolean)=>void}){
 const [text,setText]=useState(JSON.stringify(value??null,null,2));const [invalid,setInvalid]=useState(false);
 useEffect(()=>()=>onValidity?.(label,false),[onValidity,label]);
 return <label>{label}<textarea aria-label={label} rows={4} value={text} aria-invalid={invalid} onChange={e=>{setText(e.target.value);try{const parsed=JSON.parse(e.target.value);if(parsed!==null&&!Array.isArray(parsed))throw new Error();setInvalid(false);onValidity?.(label,false);onChange(parsed);}catch{setInvalid(true);onValidity?.(label,true);}}}/>{invalid&&<small role="alert">Enter a JSON array or null.</small>}</label>;
}
