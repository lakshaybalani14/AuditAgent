import { useMemo, useState } from "react";

const ACTIONS = {
  0: "No change",
  1: "Switch to Round Robin",
  2: "Switch to Priority",
  3: "Switch to MLFQ",
  4: "Boost longest-waiting process",
};
const POLICIES = ["Round Robin", "Priority", "MLFQ"];

function number(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(1) : "—";
}

export default function OrbitalTimeline({ decisions = [], loading = false }) {
  const events = useMemo(() => decisions.slice(-8).reverse(), [decisions]);
  const [selectedKey, setSelectedKey] = useState(null);
  const selected = events.find((event) => `${event?.state?.time}-${event?.action}` === selectedKey) || events[0];

  if (!events.length) {
    return <section className="panel orbital-panel"><p className="eyebrow">AGENT ACTIVITY</p><h3>Decision orbit</h3><p className="chart-empty">{loading ? "Waiting for decisions…" : "No decisions recorded for this run yet."}</p></section>;
  }

  return (
    <section className="panel orbital-panel">
      <div className="panel-heading">
        <div><p className="eyebrow">AGENT ACTIVITY</p><h3>Decision orbit</h3></div>
        <span className="feed-count">Latest {events.length} / {decisions.length}</span>
      </div>
      <div className="orbit-layout">
        <div className="orbit-stage" aria-label="Recent scheduler decisions arranged around the live run">
          <div className="orbit-ring orbit-ring-outer" />
          <div className="orbit-ring orbit-ring-inner" />
          <div className="orbit-center"><span className="orbit-center-pulse" /><b>LIVE</b><small>RUN</small></div>
          {events.map((event, index) => {
            const angle = (-90 + index * (360 / events.length)) * (Math.PI / 180);
            const x = 50 + Math.cos(angle) * 39;
            const y = 50 + Math.sin(angle) * 39;
            const key = `${event?.state?.time}-${event?.action}`;
            const active = selected && `${selected?.state?.time}-${selected?.action}` === key;
            return (
              <button
                key={`${key}-${index}`}
                className={`orbit-node${active ? " is-selected" : ""}${index === 0 ? " is-latest" : ""}`}
                style={{ left: `${x}%`, top: `${y}%`, "--node-delay": `${index * 70}ms` }}
                onClick={() => setSelectedKey(key)}
                aria-pressed={Boolean(active)}
                aria-label={`Tick ${event?.state?.time ?? "unknown"}: ${event?.action_name || ACTIONS[event?.action] || "Unknown action"}`}
              >
                <span>{event?.state?.time ?? "—"}</span>
              </button>
            );
          })}
        </div>
        {selected && <div className="orbit-detail" key={`${selected?.state?.time}-${selected?.action}`}>
          <div className="orbit-detail-top"><span className="eyebrow">TICK {selected?.state?.time ?? "—"}</span><span className="orbit-policy">{POLICIES[selected?.state?.current_algo] || "Scheduler"}</span></div>
          <h4>{selected?.action_name || ACTIONS[selected?.action] || "Unknown action"}</h4>
          <p>Queue <b>{selected?.state?.queue_length ?? "—"}</b><span>·</span> average wait <b>{number(selected?.state?.avg_wait_time)}</b></p>
          <div className="orbit-detail-rule" />
          <p className="orbit-explanation">{selected?.explanation || (selected?.explanation_status === "unavailable" ? selected?.explanation_error || "Cloud explanation unavailable. The recorded decision is still shown." : "No cloud explanation saved. Decision details are available from the recorded scheduler state.")}</p>
          {selected?.state?.is_starving && <span className="orbit-risk">Starvation risk detected</span>}
        </div>}
      </div>
      <div className="orbit-caption"><span><i className="orbit-dot orbit-dot-latest" /> Latest decision</span><span><i className="orbit-dot" /> Select a tick to inspect</span></div>
    </section>
  );
}
