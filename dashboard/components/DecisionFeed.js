import { useState } from "react";

const ACTION_LABELS = {
  0: "No change",
  1: "Switch to Round Robin",
  2: "Switch to Priority",
  3: "Switch to MLFQ",
  4: "Boost longest-waiting process",
};

function formatNumber(value, digits = 1) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
}

export default function DecisionFeed({ decisions = [], loading }) {
  const [expanded, setExpanded] = useState(null);
  const visibleDecisions = decisions.slice().reverse();
  const isSamplePreview = decisions.some((entry) => entry?.source === "sample_preview");

  return (
    <section className="panel decision-panel">
      <div className="panel-heading">
        <div><p className="eyebrow">FULL RUN HISTORY</p><h3>Decision log</h3></div>
        <span className="feed-count">{decisions.length} events</span>
      </div>
      {isSamplePreview && <div className="sample-report-banner" role="status"><strong>Sample decisions</strong><span>Generated preview data; this is not a trained agent run.</span></div>}
      {!loading && !decisions.length ? (
        <div className="empty-feed">No decisions recorded for this run yet.</div>
      ) : (
        <div className="decision-list">
          {visibleDecisions.map((entry, index) => {
            const state = entry?.state || {};
            const originalIndex = decisions.length - index - 1;
            const open = expanded === originalIndex;
            const label = entry?.action_name || ACTION_LABELS[entry?.action] || "Unknown action";
            const key = `${state.time ?? "time"}-${entry?.action ?? "action"}-${originalIndex}`;

            return (
              <article className={open ? "decision-card expanded" : "decision-card"} key={key}>
                <button
                  className="decision-button"
                  aria-expanded={open}
                  onClick={() => setExpanded(open ? null : originalIndex)}
                >
                  <span className="time-chip">t {state.time ?? "—"}</span>
                  <span className="decision-main">
                    <b>{label}</b>
                    <small>Queue {state.queue_length ?? "—"} · avg wait {formatNumber(state.avg_wait_time)}</small>
                  </span>
                  <span className="chevron" aria-hidden="true">⌄</span>
                </button>
                {open && (
                  <div className="decision-detail">
                    <dl className="decision-state">
                      <div><dt>Scheduling policy</dt><dd>{["Round Robin", "Priority", "MLFQ"][state.current_algo] || "Unknown"}</dd></div>
                      <div><dt>Longest wait</dt><dd>{formatNumber(state.max_wait_time)} ticks</dd></div>
                      <div><dt>I/O bound</dt><dd>{state.num_io_bound ?? "—"}</dd></div>
                      <div><dt>CPU bound</dt><dd>{state.num_cpu_bound ?? "—"}</dd></div>
                      <div><dt>Starvation risk</dt><dd>{state.is_starving ? "Detected" : "Not detected"}</dd></div>
                    </dl>
                    <p className="explanation-label">Explanation</p>
                    <p>
                      {entry?.explanation || (entry?.explanation_status === "unavailable"
                        ? entry?.explanation_error || "The explanation provider could not explain this decision. The recorded state and action are still available above."
                        : "No AI explanation was saved. The recorded state and action are still available above; the dashboard does not require an API key.")}
                    </p>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
