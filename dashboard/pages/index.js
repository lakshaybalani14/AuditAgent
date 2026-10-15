import { useMemo } from "react";
import Link from "next/link";
import DashboardLayout from "../components/DashboardLayout";
import QueueView from "../components/QueueView";
import OrbitalTimeline from "../components/OrbitalTimeline";
import RunCharts from "../components/RunCharts";
import useDashboardData from "../hooks/useDashboardData";
function formatMetric(value,digits=1) { return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—"; }
export default function Overview() {
  const data = useDashboardData();
  const latestState = data.decisions.at(-1)?.state || null;
  const interventions = useMemo(() => data.decisions.filter((item) => item.action !== 0).length,[data.decisions]);
  const status = data.reportStatus === "sample" ? "Sample preview" : data.reportStatus === "available" ? "Report loaded" : "Awaiting report";
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun}>
    <section className="hero"><div><p className="eyebrow">SCHEDULER RUN MONITOR</p><h2>Scheduling, <em>explained.</em></h2><p className="hero-copy">A live view of scheduler health, workload pressure, and agent decisions.</p></div><div className="run-meta"><span>RECORDED DECISIONS</span><strong>{data.decisions.length}</strong><small>Live state from the decision log</small></div></section>
    <section className="metric-grid"><div className="metric-card"><span>Latest queue depth</span><strong>{latestState?.queue_length ?? "—"}</strong><small>ready processes</small></div><div className="metric-card"><span>Average queue age</span><strong>{latestState ? formatMetric(latestState.avg_wait_time) : "—"}</strong><small>ticks in ready queue</small></div><div className="metric-card"><span>Agent interventions</span><strong>{interventions}</strong><small>policy changes and priority boosts</small></div><div className="metric-card"><span>Starvation risk</span><strong className={latestState?.is_starving ? "danger" : "safe"}>{latestState ? latestState.is_starving ? "HIGH" : "CLEAR" : "—"}</strong><small>from the latest recorded state</small></div></section>
    <RunCharts decisions={data.decisions} />
    <section className="dashboard-grid"><QueueView state={latestState} decisions={data.decisions} /><OrbitalTimeline decisions={data.decisions} loading={data.loading} /></section>
    <Link href="/evaluation" className="overview-report-link"><span><b>{data.report ? "Evaluation report ready" : "Evaluation report not available yet"}</b><small>{data.report ? "Open policy comparisons and workload results" : "The Overview and Decision log work while waiting for the trained model"}</small></span><strong>{data.report ? "View evaluation →" : "Why? →"}</strong></Link>
  </DashboardLayout>;
}
