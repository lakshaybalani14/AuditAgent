import { useId, useState } from "react";
import { formatProcessId } from "../lib/processDisplay";

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

function DecisionIcon({ action }) {
  const shapes = {
    0: <><path d="M9 5v14M15 5v14" /></>,
    1: <><path d="M20 7h-9a6 6 0 0 0-6 6M16 3l4 4-4 4M4 17h9a6 6 0 0 0 6-6M8 21l-4-4 4-4" /></>,
    2: <><path d="M5 19h3M5 14h6M5 9h9M18 19V5M15 8l3-3 3 3" /></>,
    3: <><path d="m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5" /></>,
    4: <><circle cx="10" cy="13" r="7" /><path d="M10 9v4l3 2M18 10V3M15 6l3-3 3 3" /></>,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{shapes[action] || shapes[0]}</svg>;
}

function actionCategory(action) {
  if (action === 0) return "Hold policy";
  if (action === 4) return "Priority boost";
  if ([1, 2, 3].includes(action)) return "Policy choice";
  return "Action";
}

function explanationStatus(entry) {
  if (entry?.explanation) return "Explanation saved";
  if (entry?.explanation_status === "pending") return "Explanation pending";
  if (entry?.explanation_status === "unavailable") return "Explanation unavailable";
  return "No explanation requested";
}

export default function DecisionFeed({ decisions = [], loading }) {
  const idPrefix = useId();
  const [expanded, setExpanded] = useState(null);
  const visibleDecisions = decisions.slice().reverse();
  const isSamplePreview = decisions.some((entry) => entry?.source === "sample_preview");

  return (
    <section className="panel decision-panel activity-log" aria-label="Recorded scheduler decisions">
      <div className="activity-log-header">
        <h3>Scheduler activity</h3>
        <span className="feed-count">Current run · {decisions.length} decisions</span>
      </div>
      {isSamplePreview && <div className="sample-report-banner" role="status"><strong>Sample decisions</strong><span>Generated preview data; this is not a trained agent run.</span></div>}
      {!decisions.length ? (
        <div className="empty-feed" role="status">{loading ? "Loading decisions…" : "No decisions recorded for this run yet."}</div>
      ) : (
        <ul className="decision-list activity-events">
          {visibleDecisions.map((entry, index) => {
            const state = entry?.state || {};
            const originalIndex = decisions.length - index - 1;
            const open = expanded === originalIndex;
            const label = entry?.action_name || ACTION_LABELS[entry?.action] || "Unknown action";
            const key = `${state.time ?? "time"}-${entry?.action ?? "action"}-${originalIndex}`;
            const detailId = `${idPrefix}-decision-${originalIndex}`;

            return (
              <li className={`decision-card activity-event${open ? " expanded" : ""}`} key={key}>
                <button
                  className="decision-button activity-event-button"
                  aria-expanded={open}
                  aria-controls={detailId}
                  onClick={() => setExpanded(open ? null : originalIndex)}
                >
                  <span className={`activity-event-icon activity-action-${entry?.action}`}><DecisionIcon action={entry?.action} /></span>
                  <span className="activity-event-copy">
                    <span className="activity-event-title"><strong>{label}</strong><span className={`activity-action-tag activity-action-${entry?.action}`}>{actionCategory(entry?.action)}</span></span>
                    <span className="activity-event-description">Episode {entry?.episode ?? "—"} · Step {entry?.step ?? originalIndex + 1} · Ready queue {state.queue_length ?? "—"} · Average wait {formatNumber(state.avg_wait_time)} ticks</span>
                    <span className={`activity-explanation-status explanation-${entry?.explanation ? "available" : entry?.explanation_status || "not_configured"}`}><i aria-hidden="true" />{explanationStatus(entry)}</span>
                  </span>
                  <span className="activity-event-time" aria-label={`Simulator tick ${state.time ?? "unknown"}`}>Tick {state.time ?? "—"}</span>
                  <span className="chevron" aria-hidden="true">⌄</span>
                </button>
                {open && (
                  <div className="decision-detail" id={detailId}>
                    <p className="decision-context">
                      The DQN selected this action from the state shown below. The simulator then applied it and advanced one step.
                    </p>
                    <dl className="decision-state">
                      <div><dt>Scheduling policy</dt><dd>{["Round Robin", "Priority", "MLFQ"][state.current_algo] || "Unknown"}</dd></div>
                      <div><dt>Longest wait</dt><dd>{formatNumber(state.max_wait_time)} ticks</dd></div>
                      <div><dt>I/O bound</dt><dd>{state.num_io_bound ?? "—"}</dd></div>
                      <div><dt>CPU bound</dt><dd>{state.num_cpu_bound ?? "—"}</dd></div>
                      <div><dt>Starvation risk</dt><dd>{state.is_starving ? "Detected" : "Not detected"}</dd></div>
                      <div><dt>Reward this step</dt><dd>{formatNumber(entry?.reward, 2)}</dd></div>
                      <div><dt>Scheduler changed</dt><dd>{entry?.scheduler_changed ? "Yes" : "No"}</dd></div>
                      <div><dt>Processes in workload</dt><dd>{entry?.processes?.length ?? "—"}</dd></div>
                    </dl>
                    {entry?.resulting_state && (
                      <div className="decision-outcome">
                        <p className="explanation-label">After the simulator step</p>
                        <div>
                          <span>Policy <b>{["Round Robin", "Priority", "MLFQ"][entry.resulting_state.current_algo] || "Unknown"}</b></span>
                          <span>Ready queue <b>{entry.resulting_state.queue_length ?? "—"}</b></span>
                          <span>Average wait <b>{formatNumber(entry.resulting_state.avg_wait_time)} ticks</b></span>
                          <span>Simulator tick <b>{entry.resulting_state.time ?? "—"}</b></span>
                        </div>
                      </div>
                    )}
                    {Object.keys(entry?.q_values || {}).length > 0 && (
                      <div className="dqn-readout">
                        <p className="explanation-label">DQN action values</p>
                        <small>Estimated future reward for each available action; the highest value is preferred.</small>
                        <div className="q-value-list">{Object.entries(entry.q_values).map(([name, value]) => (
                          <div className={name === entry.action_name ? "q-value selected" : "q-value"} key={name}>
                            <span>{name}{name === entry.action_name ? " · chosen" : ""}</span>
                            <b>{formatNumber(value, 3)}</b>
                          </div>
                        ))}</div>
                      </div>
                    )}
                    {Object.keys(entry?.observation || {}).length > 0 && (
                      <details className="model-input-details">
                        <summary>Exact 20-feature input the DQN received</summary>
                        <dl className="model-input-grid">{Object.entries(entry.observation).map(([name, value]) => (
                          <div key={name}><dt>{name.replaceAll("_", " ")}</dt><dd>{formatNumber(value, 3)}</dd></div>
                        ))}</dl>
                      </details>
                    )}
                    {entry?.processes?.length > 0 && (
                      <div className="observed-processes">
                        <p className="explanation-label">Processes the agent observed</p>
                        <div>{entry.processes.map((process) => (
                          <span key={process.pid}>
                            {formatProcessId(process.pid)} {String(process.state || "unknown").toLowerCase()} · {process.remaining_time}/{process.burst_time} CPU · wait {process.waiting_time}
                          </span>
                        ))}</div>
                      </div>
                    )}
                    <p className="explanation-label">
                      {entry?.explanation_provider === "gemini" ? "Gemini explanation after the action" : "Explanation"}
                    </p>
                    <p>
                      {entry?.explanation || (entry?.explanation_status === "pending"
                        ? "Gemini is generating an explanation for this recorded state and action…"
                        : entry?.explanation_status === "unavailable"
                          ? entry?.explanation_error || "The explanation provider could not explain this decision. The recorded state and action are still available above."
                          : "No AI explanation was saved. The recorded state and action are still available above; the dashboard does not require an API key.")}
                    </p>
                    {entry?.explanation_provider === "gemini" && entry?.explanation && (
                      <small className="explanation-caveat">Gemini explains the recorded state and action after the DQN chose it. This is not the DQN's private internal reasoning.</small>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
