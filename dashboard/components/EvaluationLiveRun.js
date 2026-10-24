import AnimatedContent from "./AnimatedContent";

const revealProps = { distance: 100, direction: "vertical", duration: 0.8, ease: "power3.out", blur: 0, stagger: 0.08, threshold: 0.1 };

function formatMetric(value, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : "—";
}

function formatPercent(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
}

export default function EvaluationLiveRun({ liveRun, runStatus }) {
  const activeRun = runStatus?.status === "running";
  const matchesActiveRun = liveRun?.runId && liveRun.runId === runStatus?.id;
  const waitingForFirstDecision = activeRun && !matchesActiveRun;

  return (
    <AnimatedContent {...revealProps} as="section" className="panel live-run-panel" aria-labelledby="live-run-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">CURRENT MODEL · LIVE SIMULATOR</p>
          <h3 id="live-run-title">Latest live simulation</h3>
        </div>
        <span className={`feed-count${activeRun ? " live-run-active" : ""}`}>
          {waitingForFirstDecision
            ? "Waiting for first decision"
            : activeRun
              ? "Updating live"
              : liveRun
                ? "Latest saved run"
                : "No live run yet"}
        </span>
      </div>

      {waitingForFirstDecision && (
        <p className="live-run-note">The simulator is starting. This panel will update as soon as its first real decision is written.</p>
      )}
      {!liveRun ? (
        <p className="live-run-note">Run the live simulation from the navbar to see the DQN’s current simulator results here.</p>
      ) : (
        <>
          {liveRun.runId && runStatus?.id && !matchesActiveRun && (
            <p className="live-run-note">The current run has not written a decision yet, so these values still describe the previous run.</p>
          )}
          <div className="live-run-metrics">
            <div><span>Agent decisions</span><strong>{liveRun.decisionCount}</strong></div>
            <div><span>Episodes touched</span><strong>{liveRun.episodesObserved}</strong></div>
            <div><span>Simulation tick</span><strong>{liveRun.simulationTick ?? "—"}</strong></div>
            <div><span>Current scheduler</span><strong>{liveRun.scheduler}</strong></div>
            <div><span>Ready queue</span><strong>{liveRun.readyQueueDepth ?? "—"} processes</strong></div>
            <div><span>Current queue age</span><strong>{formatMetric(liveRun.meanReadyQueueAgeTicks)} ticks</strong></div>
            <div><span>Processes completed so far</span><strong>{liveRun.processesCompleted}/{liveRun.processesObserved} · {formatPercent(liveRun.completionRate)}</strong></div>
            <div><span>Mean wait of completed processes</span><strong>{formatMetric(liveRun.meanCompletedWaitingTimeTicks)} ticks</strong></div>
          </div>
          <div className="live-run-footer">
            <span>{liveRun.starvationRisk === null ? "Starvation status unavailable" : liveRun.starvationRisk ? "Starvation threshold reached" : "No starvation threshold reached"}</span>
            <span>{liveRun.updatedAt ? `Last decision saved ${new Date(liveRun.updatedAt).toLocaleTimeString()}` : "Decision timestamp unavailable"}</span>
          </div>
          <p className="live-run-note">This is a live trace snapshot, not the held-out benchmark. The dashboard run records up to 15 DQN decisions, so an episode may still be in progress. Completed-process averages include only processes that finished in the recorded episodes.</p>
        </>
      )}
    </AnimatedContent>
  );
}
