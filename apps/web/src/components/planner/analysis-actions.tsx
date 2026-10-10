"use client";

export function AnalysisActions({
  transfersAllowed,
  busy,
  dirty,
  stale,
  hasState,
  onRun,
  onLineup,
}: {
  transfersAllowed: boolean;
  busy: boolean;
  dirty: boolean;
  stale: boolean;
  hasState: boolean;
  onRun: () => void;
  onLineup: () => void;
}) {
  const blocked = !hasState || busy || dirty || stale;
  return (
    <div className="planner-actions">
      <button className="button" type="button" disabled={blocked || !transfersAllowed} onClick={onRun}>
        Run analysis <span aria-hidden="true">↗</span>
      </button>
      {!transfersAllowed && hasState ? (
        <button className="button secondary" type="button" disabled={blocked} onClick={onLineup}>Run lineup only</button>
      ) : null}
    </div>
  );
}

export function TransferGate({ reason }: { reason: string | null }) {
  if (!reason) return <p role="status">Transfer analysis can run.</p>;
  return <p className="warning" role="status">{reason}</p>;
}
