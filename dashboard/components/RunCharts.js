function RunCharts({ decisions = [] }) {
  const points = decisions.slice(-24);
  const maxQueue = Math.max(1, ...points.map((entry) => Number(entry?.state?.queue_length) || 0));
  const maxWait = Math.max(1, ...points.map((entry) => Number(entry?.state?.avg_wait_time) || 0));
  const queuePath = points.map((entry, index) => `${index ? "L" : "M"} ${index * (280 / Math.max(1, points.length - 1))} ${70 - ((Number(entry?.state?.queue_length) || 0) / maxQueue) * 58}`).join(" ");
  const waitPath = points.map((entry, index) => `${index ? "L" : "M"} ${index * (280 / Math.max(1, points.length - 1))} ${70 - ((Number(entry?.state?.avg_wait_time) || 0) / maxWait) * 58}`).join(" ");
  const actions = [
    { label: "No change", count: decisions.filter((entry) => entry?.action === 0).length },
    { label: "Policy switch", count: decisions.filter((entry) => [1, 2, 3].includes(entry?.action)).length },
    { label: "Priority boost", count: decisions.filter((entry) => entry?.action === 4).length },
  ];
  const peak = Math.max(1, ...actions.map((item) => item.count));
  return <section className="charts-grid" aria-label="Run charts">
    <article className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">LIVE SIGNAL</p><h3>Queue pressure</h3></div><span className="chart-legend"><i className="legend-queue" /> queue <i className="legend-wait" /> avg wait</span></div>
      {points.length > 1 ? <div className="chart-wrap"><svg className="trend-chart" viewBox="0 0 280 80" role="img" aria-label={`Queue depth and average wait over the latest ${points.length} decisions`} preserveAspectRatio="none">{[12,41,70].map((y) => <line key={y} x1="0" x2="280" y1={y} y2={y} className="chart-gridline" />)}<path d={queuePath} className="chart-line chart-line-queue" /><path d={waitPath} className="chart-line chart-line-wait" /></svg><div className="chart-axis"><span>older decisions</span><span>latest</span></div></div> : <p className="chart-empty">A trend appears after at least two decisions are recorded.</p>}
    </article>
    <article className="panel chart-panel action-chart"><div className="panel-heading"><div><p className="eyebrow">DECISION MIX</p><h3>Agent actions</h3></div><span className="feed-count">{decisions.length} total</span></div><div className="action-bars">{actions.map((item,index) => <div className="action-bar-row" key={item.label}><span>{item.label}</span><div className="action-track"><i style={{ "--bar-width": `${(item.count / peak) * 100}%`, "--bar-delay": `${index * 90}ms` }} /></div><b>{item.count}</b></div>)}</div></article>
  </section>;
}
export default RunCharts;
