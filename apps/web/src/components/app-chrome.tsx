"use client";

import Link from "next/link";
import type { ReactNode } from "react";

const sections = [
  ["overview", "Overview", "◫", "/"],
  ["players", "Players", "≋", "/players"],
  ["planner", "Planner", "↗", "/planner"],
  ["history", "Saved plans", "◷", "/history"],
  ["models", "Models", "◇", "/models"],
  ["settings", "Settings", "⚙", "/settings"],
] as const;

export function AppChrome({
  season,
  dataMode,
  busy,
  progress,
  activeJob,
  error,
  notice,
  dirty,
  stale,
  onCancel,
  children,
}: {
  season?: string;
  dataMode?: string;
  busy: string;
  progress: number;
  activeJob: string | null;
  error: string;
  notice: string;
  dirty: boolean;
  stale: boolean;
  onCancel: () => void;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <aside className="sidebar">
        <Link className="brand" href="/">
          <span className="brand-mark">t.</span>
          <span>
            touchline<small>FPL ASSISTANT</small>
          </span>
        </Link>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {sections.map(([id, name, icon, href]) => (
            <Link key={id} href={href} aria-current={id === "planner" ? "page" : undefined}>
              <span aria-hidden="true">{icon}</span>
              {name}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="dot" /> Local workspace
          <p>
            Your team. Your decisions.
            <br />
            Transfers are always manual.
          </p>
        </div>
      </aside>
      <div className="content">
        <header className="topbar">
          <span>
            Fantasy Premier League <span className="muted">/ {season || "Personal workspace"}</span>
          </span>
          <span className={`tag ${dataMode === "demo" ? "amber" : ""}`}>
            {dataMode === "demo" ? "SYNTHETIC DEMO" : dataMode ? "LIVE DATA" : "LOCAL TOOL"}
          </span>
        </header>
        <main id="main">
          {busy ? (
            <div role="status" className="feedback">
              <span className="spinner" />
              {busy}
              {activeJob ? (
                <>
                  <progress
                    max={100}
                    value={progress <= 1 ? progress * 100 : progress}
                    aria-label="Analysis progress"
                  />
                  <button className="text-button" type="button" onClick={onCancel}>
                    Cancel
                  </button>
                </>
              ) : null}
            </div>
          ) : null}
          {error ? (
            <div role="alert" className="feedback error">
              {error}
            </div>
          ) : null}
          {notice ? (
            <div role="status" className="feedback success">
              {notice}
            </div>
          ) : null}
          {dirty ? (
            <div className="feedback warning">
              Unsaved corrections. Save manager inputs before analysis.
            </div>
          ) : null}
          {stale ? (
            <div className="feedback warning">
              Manager state uses an older snapshot. Review prices and save corrections to reconcile.
            </div>
          ) : null}
          {children}
          <footer>
            Built for thoughtful decisions. All FPL actions are manual.{" "}
            <span>Local · Free data · Transparent baseline</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
