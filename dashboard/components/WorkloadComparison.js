import { Fragment, useState } from "react";
import { formatMetric, formatPercent, isMetric } from "../lib/evaluationDisplay";
import AnimatedContent from "./AnimatedContent";

const revealProps = { distance: 100, direction: "vertical", duration: 0.8, ease: "power3.out", blur: 0, stagger: 0.08, threshold: 0.1 };

const METRIC_GROUPS = [
  {
    label: "Process latency",
    metrics: [
      { key: "mean_process_waiting_time_ticks", label: "Mean waiting time", unit: " ticks", direction: "min" },
      { key: "mean_p95_process_waiting_time_ticks", label: "P95 waiting time", unit: " ticks", direction: "min" },
      { key: "mean_process_turnaround_time_ticks", label: "Turnaround time", unit: " ticks", direction: "min" },
      { key: "mean_process_response_time_ticks", label: "Response time", unit: " ticks", direction: "min" },
    ],
  },
  {
    label: "Completion and capacity",
    metrics: [
      { key: "mean_process_completion_rate", label: "Process completion", percent: true, digits: 1, direction: "max" },
      { key: "mean_cpu_utilization", label: "CPU utilization", percent: true, digits: 3, direction: "max" },
      { key: "mean_throughput_processes_per_tick", label: "Throughput", digits: 5, unit: "/tick", direction: "max" },
    ],
  },
  {
    label: "Fairness",
    metrics: [
      { key: "mean_starvation_steps", label: "Starvation steps per episode", unit: " steps", direction: "min" },
    ],
  },
];

function profileLabel(profile) {
  return profile.replaceAll("_", " ");
}

export default function WorkloadComparison({ entries, configuredProfiles = [] }) {
  const [selectedProfile, setSelectedProfile] = useState(null);
  const profiles = [...new Set([
    ...(Array.isArray(configuredProfiles) ? configuredProfiles : []),
    ...entries.flatMap(([, result]) => Object.keys(result?.by_profile || {})),
  ])].filter((profile) => entries.some(([, result]) => result?.by_profile?.[profile]));
  const activeProfile = profiles.includes(selectedProfile) ? selectedProfile : profiles[0];

  return <AnimatedContent {...revealProps} as="section" className="workload-comparison panel" aria-labelledby="workload-comparison-title">
    <div className="workload-comparison-intro">
      <span className="workload-comparison-badge">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true"><path d="M4 7h16M4 17h16M8 4v6m8 4v6" /></svg>
        Workload comparison
      </span>
      <h3 id="workload-comparison-title">Compare schedulers on the same workload</h3>
      <p>Select a profile to compare process latency, completion, capacity, and fairness side by side.</p>
    </div>
    {!profiles.length ? <p className="report-note">This report has no profile-level summaries.</p> : <>
      <div className="workload-profile-picker" role="group" aria-label="Workload profile">
        {profiles.map((profile) => <button type="button" key={profile} aria-pressed={activeProfile === profile} onClick={() => setSelectedProfile(profile)}>{profileLabel(profile)}</button>)}
      </div>
      <div className="workload-table-wrap" role="region" aria-label={`${profileLabel(activeProfile)} scheduler comparison`} tabIndex={0}>
        <table className="workload-comparison-table">
          <caption><strong>{profileLabel(activeProfile)}</strong><span>Saved profile averages. Lower latency and starvation are preferred; completion, CPU use, and throughput are shown with higher values marked.</span></caption>
          <thead><tr>
            <th scope="col">Metric</th>
            {entries.map(([name]) => <th scope="col" key={name} className={name === "DQN" ? "workload-agent-column" : undefined}>
              <div className="workload-policy-heading"><span>{name === "DQN" ? "Learned policy" : "Fixed policy"}</span><strong>{name}</strong><small>{name === "DQN" ? "Agent chooses actions" : "Baseline scheduler"}</small></div>
            </th>)}
          </tr></thead>
          <tbody>{METRIC_GROUPS.map((group) => <Fragment key={group.label}>
            <tr className="workload-metric-group"><th scope="rowgroup" colSpan={entries.length + 1}>{group.label}</th></tr>
            {group.metrics.map((metric) => {
              const values = entries.map(([, result]) => result?.by_profile?.[activeProfile]?.[metric.key]);
              const complete = values.every(isMetric);
              const extreme = complete ? (metric.direction === "min" ? Math.min(...values) : Math.max(...values)) : null;
              return <tr key={metric.key}>
                <th scope="row"><span>{metric.label}</span><small>{metric.direction === "min" ? "↓ Lower" : "↑ Higher"}</small></th>
                {entries.map(([name], index) => {
                  const value = values[index];
                  const marked = complete && Math.abs(value - extreme) <= 1e-9 * Math.max(1, Math.abs(extreme));
                  const display = metric.percent ? formatPercent(value, metric.digits) : formatMetric(value, metric.digits);
                  return <td key={name} className={name === "DQN" ? "workload-agent-column" : undefined}>
                    <span className={`workload-metric-value${marked ? " workload-metric-extreme" : ""}`} title={isMetric(value) ? `Stored value: ${value}${marked ? ` · ${metric.direction === "min" ? "Lowest" : "Highest"} observed value` : ""}` : "Metric not present in this report"}>
                      {marked && <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>}
                      <span>{display}{isMetric(value) ? metric.unit || "" : ""}</span>
                      {marked && <span className="workload-sr-only"> ({metric.direction === "min" ? "lowest" : "highest"} observed value)</span>}
                    </span>
                  </td>;
                })}
              </tr>;
            })}
          </Fragment>)}</tbody>
        </table>
      </div>
      <p className="workload-comparison-note">Check marks identify the lowest or highest recorded averages for each row, including ties. They do not establish statistical significance or an overall winning scheduler. Missing metrics appear as —.</p>
    </>}
  </AnimatedContent>;
}
