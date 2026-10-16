const SCHEDULER_NAMES = {
  0: "Round Robin",
  1: "Priority",
  2: "MLFQ",
};

function mean(values) {
  return values.length
    ? values.reduce((total, value) => total + value, 0) / values.length
    : null;
}

function finiteValues(processes, key) {
  return processes
    .map((process) => Number(process?.[key]))
    .filter(Number.isFinite);
}

/** Summarize the latest snapshot for each episode in the live decision trace. */
export function summarizeLiveRun(decisions, { source, updatedAt } = {}) {
  if (!Array.isArray(decisions) || decisions.length === 0) return null;

  const finalDecisionByEpisode = new Map();
  const actionCounts = {};
  for (const decision of decisions) {
    const episode = Number.isFinite(Number(decision?.episode))
      ? Number(decision.episode)
      : 1;
    finalDecisionByEpisode.set(episode, decision);
    const action = decision?.action_name;
    if (typeof action === "string" && action) {
      actionCounts[action] = (actionCounts[action] || 0) + 1;
    }
  }

  const observedProcesses = [...finalDecisionByEpisode.values()].flatMap((decision) =>
    Array.isArray(decision?.processes_after) ? decision.processes_after : []
  );
  const completedProcesses = observedProcesses.filter(
    (process) => String(process?.state).toUpperCase() === "COMPLETED"
  );
  const latest = decisions[decisions.length - 1];
  const state = latest?.resulting_state || {};
  const runIdMatch = typeof source === "string"
    ? source.match(/\.live-([0-9a-f-]+)(?:\.[^.]+)?$/i)
    : null;

  return {
    runId: runIdMatch?.[1] || null,
    source: source || null,
    updatedAt: updatedAt || null,
    decisionCount: decisions.length,
    episodesObserved: finalDecisionByEpisode.size,
    simulationTick: Number.isFinite(Number(state.time)) ? Number(state.time) : null,
    scheduler: SCHEDULER_NAMES[Number(state.current_algo)] || "Unknown",
    readyQueueDepth: Number.isFinite(Number(state.queue_length))
      ? Number(state.queue_length)
      : null,
    meanReadyQueueAgeTicks: Number.isFinite(Number(state.avg_wait_time))
      ? Number(state.avg_wait_time)
      : null,
    starvationRisk: typeof state.is_starving === "boolean" ? state.is_starving : null,
    processesObserved: observedProcesses.length,
    processesCompleted: completedProcesses.length,
    completionRate: observedProcesses.length
      ? completedProcesses.length / observedProcesses.length
      : null,
    meanCompletedWaitingTimeTicks: mean(
      completedProcesses.map((process) => Number(process.waiting_time)).filter(Number.isFinite)
    ),
    meanCompletedResponseTimeTicks: mean(
      completedProcesses.map((process) => Number(process.response_time)).filter(Number.isFinite)
    ),
    meanCompletedTurnaroundTimeTicks: mean(
      completedProcesses.map((process) => Number(process.turnaround_time)).filter(Number.isFinite)
    ),
    actionCounts,
  };
}
