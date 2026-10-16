import AnimatedNumber from "./AnimatedNumber";
import FlapHeadingText from "./FlapHeadingText";

function RunCharts({ decisions = [] }) {
  const actions = [
    { label: "No change", count: decisions.filter((entry) => entry?.action === 0).length },
    { label: "Round Robin", count: decisions.filter((entry) => entry?.action === 1).length },
    { label: "Priority", count: decisions.filter((entry) => entry?.action === 2).length },
    { label: "MLFQ", count: decisions.filter((entry) => entry?.action === 3).length },
    { label: "Wait boost", count: decisions.filter((entry) => entry?.action === 4).length, title: "Boost longest-waiting process" },
  ];
  return <article className="panel chart-panel action-chart" aria-labelledby="agent-decisions-heading">
    <div className="panel-heading"><h3 id="agent-decisions-heading"><FlapHeadingText>Agent decisions</FlapHeadingText></h3><span className="feed-count"><AnimatedNumber value={decisions.length} /> recorded</span></div>
    <div className="action-bars" aria-label="Share of recorded decisions by action">{actions.map((item,index) => {
      const share = decisions.length ? (item.count / decisions.length) * 100 : 0;
      return <div className="action-bar-row" key={item.label}>
        <span title={item.title}>{item.label}</span>
        <div className="action-track" role="meter" aria-label={`${item.label}: ${item.count} of ${decisions.length} decisions`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={share}>
          <i style={{ "--bar-width": `${share}%`, "--bar-delay": `${index * 90}ms` }} />
        </div>
        <b><AnimatedNumber value={item.count} /><small>{Math.round(share)}%</small></b>
      </div>;
    })}</div>
  </article>;
}
export default RunCharts;
