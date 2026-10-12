import type { Settings } from "../lib/api/client";

export function PlanningOptions({
  settings,
  disabled,
  onChange,
}: {
  settings: Settings;
  disabled: boolean;
  onChange: (patch: Partial<Settings>) => void;
}) {
  return (
    <>
      <label>
        Future chip proposals
        <select
          value={settings.future_chip_policy ?? "none"}
          disabled={disabled}
          onChange={(event) =>
            onChange({ future_chip_policy: event.target.value as Settings["future_chip_policy"] })
          }
        >
          <option value="none">Keep future chips</option>
          <option value="optimise">Compare legal future chip dates</option>
        </select>
      </label>
      <label>
        Planning search
        <select
          value={settings.planner_mode ?? "bounded"}
          disabled={disabled}
          onChange={(event) =>
            onChange({ planner_mode: event.target.value as Settings["planner_mode"] })
          }
        >
          <option value="bounded">Bounded transfer search</option>
          <option value="sequence">Financial sequence search</option>
        </select>
      </label>
      <p className="muted">
        Future chips use confirmed inventory. Large sequence searches compare up to two replacements
        per event, including chip weeks, and report budget limits. Later actions are conditional
        proposals.
      </p>
    </>
  );
}
