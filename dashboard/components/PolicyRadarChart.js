import { useId, useState } from "react";
import { formatMetric, formatPercent, isMetric } from "../lib/evaluationDisplay";

const METRICS = [
  { key: "mean_process_waiting_time_ticks", label: "Mean waiting time", axis: "Mean wait", unit: " ticks", lower: true },
  { key: "mean_p95_process_waiting_time_ticks", label: "P95 waiting time", axis: "P95 wait", unit: " ticks", lower: true },
  { key: "mean_process_completion_rate", label: "Process completion", axis: "Completion", percent: true, digits: 1 },
  { key: "mean_cpu_utilization", label: "CPU utilization", axis: "CPU use", percent: true, digits: 3 },
  { key: "mean_throughput_processes_per_tick", label: "Throughput", axis: "Throughput", digits: 5, unit: "/tick" },
  { key: "mean_process_response_time_ticks", label: "Response time", axis: "Response time", unit: " ticks", lower: true },
];
const COLORS = ["var(--accent)", "var(--radar-blue)", "var(--radar-amber)", "var(--radar-purple)"];
const valid = (value) => isMetric(value) && value >= 0;

function point(index, score, radius = 152) {
  const angle = index * Math.PI / 3 - Math.PI / 2;
  return { x: 320 + Math.cos(angle) * radius * score / 100, y: 222 + Math.sin(angle) * radius * score / 100 };
}

function displayValue(value, metric) {
  if (!isMetric(value)) return "—";
  return metric.percent ? formatPercent(value, metric.digits) : `${formatMetric(value, metric.digits)}${metric.unit || ""}`;
}

export default function PolicyRadarChart({ entries }) {
  const chartId = useId();
  const [activeMetric, setActiveMetric] = useState(0);
  const [hiddenPolicies, setHiddenPolicies] = useState([]);
  const [focusedPolicy, setFocusedPolicy] = useState(null);
  const best = METRICS.map((metric) => {
    const values = entries.map(([, result]) => result?.summary?.[metric.key]).filter(valid);
    return values.length ? (metric.lower ? Math.min(...values) : Math.max(...values)) : null;
  });
  const series = entries.map(([name, result], index) => {
    const values = METRICS.map((metric) => result?.summary?.[metric.key]);
    const complete = values.every(valid);
    const scores = values.map((value, metricIndex) => {
      if (!valid(value) || best[metricIndex] === null) return null;
      if (value === best[metricIndex]) return 100;
      return METRICS[metricIndex].lower ? 100 * best[metricIndex] / value : 100 * value / best[metricIndex];
    });
    return { name, values, scores, complete, color: COLORS[index % COLORS.length] };
  });
  const visible = series.filter((item) => item.complete && !hiddenPolicies.includes(item.name));
  const metric = METRICS[activeMetric];
  const selectedPoint = point(activeMetric, 100);

  function togglePolicy(name) {
    setHiddenPolicies((current) => current.includes(name) ? current.filter((item) => item !== name) : [...current, name]);
  }

  return <figure className="policy-radar">
    <p className="policy-radar-intro">Overall results across the saved evaluation workloads. Further from the centre means a better relative result on that axis.</p>
    <div className="policy-radar-legend" role="group" aria-label="Visible schedulers">
      {series.map((item) => {
        const shown = item.complete && !hiddenPolicies.includes(item.name);
        return <button type="button" key={item.name} aria-pressed={shown} disabled={!item.complete || (shown && visible.length === 1)} onClick={() => togglePolicy(item.name)} onPointerEnter={() => setFocusedPolicy(item.name)} onPointerLeave={() => setFocusedPolicy(null)} onFocus={() => setFocusedPolicy(item.name)} onBlur={() => setFocusedPolicy(null)} style={{ "--policy-color": item.color }}>
          <i aria-hidden="true" />{item.name}{!item.complete && <small>Incomplete data</small>}
        </button>;
      })}
    </div>
    <div className="policy-radar-layout">
      <div className="policy-radar-canvas">
        <svg viewBox="0 0 640 450" role="group" aria-labelledby={`${chartId}-title ${chartId}-description`}>
          <title id={`${chartId}-title`}>Scheduler policy radar comparison</title>
          <desc id={`${chartId}-description`}>Six axes show relative scores from zero to one hundred. Focus an axis or select a metric to read the actual saved values. The legend toggles scheduler visibility.</desc>
          {[25, 50, 75, 100].map((score) => <g key={score} aria-hidden="true">
            <polygon className="policy-radar-grid" points={METRICS.map((_, i) => { const p = point(i, score); return `${p.x},${p.y}`; }).join(" ")} />
            <text className="policy-radar-scale" x="326" y={222 - 152 * score / 100 + 12}>{score}</text>
          </g>)}
          {METRICS.map((_, index) => { const p = point(index, 100); return <line key={index} className="policy-radar-spoke" x1="320" y1="222" x2={p.x} y2={p.y} aria-hidden="true" />; })}
          {[...visible].reverse().map((item) => <g key={item.name} className={`policy-radar-series${focusedPolicy && focusedPolicy !== item.name ? " is-muted" : ""}`} style={{ "--policy-color": item.color }} aria-hidden="true">
            <polygon points={item.scores.map((score, index) => { const p = point(index, score); return `${p.x},${p.y}`; }).join(" ")} />
            {item.scores.map((score, index) => { const p = point(index, score); return <circle key={index} cx={p.x} cy={p.y} r={activeMetric === index ? 4.5 : 2.5} onPointerEnter={() => setActiveMetric(index)} />; })}
          </g>)}
          <line className="policy-radar-active-spoke" x1="320" y1="222" x2={selectedPoint.x} y2={selectedPoint.y} aria-hidden="true" />
          {METRICS.map((item, index) => {
            const p = point(index, 100, 190);
            return <g key={item.key} className={`policy-radar-axis${activeMetric === index ? " is-active" : ""}`} role="button" tabIndex={0} aria-label={`Inspect ${item.label}`} aria-pressed={activeMetric === index} onPointerEnter={() => setActiveMetric(index)} onFocus={() => setActiveMetric(index)} onClick={() => setActiveMetric(index)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setActiveMetric(index); } }}>
              <rect x={p.x - 66} y={p.y - 18} width="132" height="41" rx="8" />
              <text x={p.x} y={p.y} textAnchor="middle">{item.axis}</text>
              <text className="policy-radar-axis-direction" x={p.x} y={p.y + 16} textAnchor="middle">{item.lower ? "↓ Lower is better" : "↑ Higher is better"}</text>
            </g>;
          })}
        </svg>
        {!visible.length && <p className="policy-radar-empty">The report needs all six metrics for at least one scheduler to draw the radar.</p>}
      </div>
      <aside className="policy-radar-tooltip" aria-label="Actual metric values">
        <label htmlFor={`${chartId}-metric`}>Inspect metric</label>
        <select id={`${chartId}-metric`} value={activeMetric} onChange={(event) => setActiveMetric(Number(event.target.value))}>
          {METRICS.map((item, index) => <option key={item.key} value={index}>{item.label}</option>)}
        </select>
        <p>{metric.lower ? "Lower is better" : "Higher is better"} · actual averages</p>
        <dl>{series.map((item) => <div key={item.name} style={{ "--policy-color": item.color }}><dt><i aria-hidden="true" />{item.name}</dt><dd title={isMetric(item.values[activeMetric]) ? `Stored value: ${item.values[activeMetric]}` : "Metric not present in this report"}>{displayValue(item.values[activeMetric], metric)}</dd></div>)}</dl>
      </aside>
    </div>
    <figcaption className="policy-radar-note"><strong>Reading the chart:</strong> Each axis is scaled to the best recorded average, which scores 100. For latency, score = best ÷ value × 100; for completion and capacity, score = value ÷ best × 100. Zero ties score 100. These are relative scores, not percentage improvements or a combined model grade. Hiding a scheduler keeps the scale unchanged.</figcaption>
    <details className="policy-radar-values"><summary>View all recorded values</summary><div className="table-wrap"><table className="policy-table"><caption>Unscaled averages from the saved evaluation report.</caption><thead><tr><th scope="col">Policy</th>{METRICS.map((item) => <th scope="col" key={item.key}>{item.axis}</th>)}</tr></thead><tbody>{series.map((item) => <tr key={item.name}><th scope="row">{item.name}</th>{item.values.map((value, index) => <td key={METRICS[index].key}>{displayValue(value, METRICS[index])}</td>)}</tr>)}</tbody></table></div></details>
  </figure>;
}
