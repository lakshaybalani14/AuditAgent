import { formatProcessId } from "../lib/processDisplay";

const ALGORITHMS = ["Round Robin", "Priority", "MLFQ"];
export default function QueueView({ state, decisions = [] }) {
  const latestDecision = decisions.at(-1);
  const liveState = latestDecision?.resulting_state || state;
  const processes = latestDecision?.processes_after || latestDecision?.processes || [];
  if (!liveState) return <section className="panel queue-panel empty-panel">Waiting for a simulator run…</section>;
  const queueSlots = Array.from({ length: Math.max(6, liveState.queue_length || 0) });
  const longestWait = Number(liveState.max_wait_time) || 0;
  return (
    <section className="panel queue-panel">
      <div className="panel-heading">
        <div><p className="eyebrow">SIMULATOR STATE</p><h3>Processes after agent action</h3></div>
        <span className="algorithm-pill">{ALGORITHMS[liveState.current_algo] || "Unknown"}</span>
      </div>
      {latestDecision && (
        <p className="simulation-action">
          <span>Agent chose</span> <strong>{latestDecision.action_name || "Unknown action"}</strong>
          <small>episode {latestDecision.episode ?? "—"} · step {latestDecision.step ?? "—"}</small>
        </p>
      )}
      <div className="queue-visual">
        <div className="queue-label"><span>READY QUEUE</span><b>{liveState.queue_length ?? 0}</b></div>
        <div className="queue-slots">{queueSlots.map((_, index) => <span key={index} className={index < liveState.queue_length ? "queue-slot active" : "queue-slot"} />)}</div>
      </div>
      <div className="wait-section">
        <div className="section-label"><span>Longest waiting process</span><b>{longestWait.toFixed(1)} ticks</b></div>
        <div className="progress-track"><span style={{ width: `${Math.min(100, (longestWait / 50) * 100)}%` }} /></div>
      </div>
      <div className="bound-grid">
        <div><span className="dot io" /> I/O bound <b>{liveState.num_io_bound ?? 0}</b></div>
        <div><span className="dot cpu" /> CPU bound <b>{liveState.num_cpu_bound ?? 0}</b></div>
      </div>
      <div className="process-table-wrap">
        <div className="process-table-heading"><strong>Simulated processes</strong><span>{processes.length} in workload</span></div>
        {processes.length ? (
          <table className="process-table">
            <thead><tr><th>PID</th><th>Status</th><th>CPU left</th><th>Wait</th><th>Priority</th></tr></thead>
            <tbody>{processes.map((process) => (
              <tr key={process.pid}>
                <th scope="row">{formatProcessId(process.pid)}</th>
                <td><span className={`process-state process-${String(process.state || "").toLowerCase()}`}>{process.state || "—"}</span></td>
                <td>{process.remaining_time ?? "—"}/{process.burst_time ?? "—"}</td>
                <td>{process.waiting_time ?? 0}</td>
                <td>{process.priority ?? "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        ) : <p className="process-empty">The simulator has not published a process snapshot yet.</p>}
      </div>
      <div className="state-footer"><span>Simulator time</span><strong>t = {liveState.time ?? "—"}</strong><small>{decisions.length} recorded decisions</small></div>
    </section>
  );
}
