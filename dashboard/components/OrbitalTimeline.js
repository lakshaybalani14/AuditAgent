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

function eventKey(event) {
  return `${event?.episode ?? "—"}-${event?.step ?? "—"}-${event?.state?.time ?? "—"}-${event?.action ?? "—"}`;
}

export default function OrbitalTimeline({ decisions = [], loading = false, runStatus }) {
  const events = useMemo(() => decisions.slice(-8).reverse(), [decisions]);
  const [selectedKey, setSelectedKey] = useState(null);
  const selected = events.find((event) => eventKey(event) === selectedKey) || events[0];
  const runLabel = runStatus?.status === "running" ? "LIVE" : events.some((event) => event?.source === "sample_preview") ? "SAMPLE" : "SAVED";

  if (!events.length) {
    return <section className="panel orbital-panel"><div className="orbit-panel-top-space" aria-hidden="true" /><p className="chart-empty">{loading ? "Waiting for decisions…" : "No decisions recorded for this run yet."}</p></section>;
  }

  return (
    <section className="panel orbital-panel">
      <div className="orbit-panel-top-space" aria-hidden="true" />
      <div className="orbit-layout">
        <div className="orbit-stage" aria-label="Recent scheduler decisions arranged around the run">
          <div className="orbit-ring orbit-ring-outer" />
          <div className="orbit-ring orbit-ring-inner" />
          <div className="orbit-center"><span className="orbit-center-pulse" /><b>{runLabel}</b><small>{runLabel === "SAMPLE" ? "DATA" : "RUN"}</small></div>
          {events.map((event, index) => {
            const angle = (-90 + index * (360 / events.length)) * (Math.PI / 180);
            const x = 50 + Math.cos(angle) * 39;
            const y = 50 + Math.sin(angle) * 39;
            const key = eventKey(event);
            const active = selected && eventKey(selected) === key;
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
        {selected && <div className="orbit-detail" key={eventKey(selected)}>
          <div className="orbit-detail-top"><span className="eyebrow">TICK {selected?.state?.time ?? "—"}</span><span className="orbit-policy">{POLICIES[selected?.state?.current_algo] || "Scheduler"}</span></div>
          <h4>{selected?.action_name || ACTIONS[selected?.action] || "Unknown action"}</h4>
          <p>Queue <b>{selected?.state?.queue_length ?? "—"}</b><span>·</span> average wait <b>{number(selected?.state?.avg_wait_time)}</b></p>
          <div className="orbit-detail-rule" />
          <p className="orbit-explanation">{selected?.explanation || (selected?.explanation_status === "pending" ? "Generating an explanation for this decision…" : selected?.explanation_status === "unavailable" ? selected?.explanation_error || "Cloud explanation unavailable. The recorded decision is still shown." : "No cloud explanation saved. Decision details are available from the recorded scheduler state.")}</p>
          {selected?.state?.is_starving && <span className="orbit-risk">Starvation risk detected</span>}
        </div>}
      </div>
      <div className="orbit-caption"><span><i className="orbit-dot orbit-dot-latest" /> Latest decision</span><span><i className="orbit-dot" /> Select a tick to inspect</span></div>
    </section>
  );
}
