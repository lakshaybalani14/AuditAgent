import { formatProcessId } from "../lib/processDisplay";

const ALGORITHMS = ["Round Robin", "Priority", "MLFQ"];
export default function QueueView({ state, decisions = [] }) {
  const latestDecision = decisions.at(-1);
  const liveState = latestDecision?.resulting_state || state;
  const processes = latestDecision?.processes_after || latestDecision?.processes || [];
  if (!liveState) return <section className="panel queue-panel empty-panel">Waiting for a simulator run…</section>;
  const readyProcesses = processes.filter((process) => process.state === "READY");
  const queueLength = Math.max(0, Number(liveState.queue_length) || 0);
  const queueSlots = Array.from({ length: Math.max(6, queueLength) }, (_, index) => {
    if (index >= queueLength) return null;
    // Older decision logs may omit per-process snapshots; use the aggregate
    // ready-queue counts for a useful color split in that case.
    const ioCount = Math.max(0, Number(liveState.num_io_bound) || 0);
    return readyProcesses[index] || { is_io_bound: index < ioCount };
  });
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
        <div className="queue-slots">{queueSlots.map((process, index) => <span key={index} className={`queue-slot${process ? ` active ${process.is_io_bound ? "io" : "cpu"}` : ""}`} />)}</div>
      </div>
      <div className="bound-grid">
        <div><span className="dot io" /><span>I/O bound</span><b className="bound-count io-count" aria-label={`${liveState.num_io_bound ?? 0} I/O-bound processes`}>{liveState.num_io_bound ?? 0}</b></div>
        <div><span className="dot cpu" /><span>CPU bound</span><b className="bound-count cpu-count" aria-label={`${liveState.num_cpu_bound ?? 0} CPU-bound processes`}>{liveState.num_cpu_bound ?? 0}</b></div>
      </div>
      <div className="process-table-wrap">
        <div className="process-table-heading"><strong>Simulated processes</strong></div>
        {processes.length ? (
          <table className="process-table">
            <thead><tr><th>Process</th><th>Type</th><th>Status</th><th>CPU left</th><th>Wait</th><th>Priority</th></tr></thead>
            <tbody>{processes.map((process) => (
              <tr key={process.pid}>
                <th scope="row">{formatProcessId(process.pid)}</th>
                <td><span className={`process-type ${process.is_io_bound ? "process-type-io" : "process-type-cpu"}`}>{process.is_io_bound ? "I/O bound" : "CPU bound"}</span></td>
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
