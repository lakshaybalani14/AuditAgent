import AnimatedNumber from "./AnimatedNumber";

function RunCharts({ decisions = [] }) {
  const actions = [
    { label: "No change", count: decisions.filter((entry) => entry?.action === 0).length },
    { label: "Policy switch", count: decisions.filter((entry) => [1, 2, 3].includes(entry?.action)).length },
    { label: "Priority boost", count: decisions.filter((entry) => entry?.action === 4).length },
  ];
  const peak = Math.max(1, ...actions.map((item) => item.count));
  return <article className="panel chart-panel action-chart" aria-labelledby="agent-decisions-heading"><div className="panel-heading"><h3 id="agent-decisions-heading">Agent decisions</h3><span className="feed-count"><AnimatedNumber value={decisions.length} /> total</span></div><div className="action-bars">{actions.map((item,index) => <div className="action-bar-row" key={item.label}><span>{item.label}</span><div className="action-track"><i style={{ "--bar-width": `${(item.count / peak) * 100}%`, "--bar-delay": `${index * 90}ms` }} /></div><b><AnimatedNumber value={item.count} /></b></div>)}</div></article>;
}
export default RunCharts;
