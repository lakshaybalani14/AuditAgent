import DashboardLayout from "../components/DashboardLayout";
import DecisionFeed from "../components/DecisionFeed";
import OrbitalTimeline from "../components/OrbitalTimeline";
import RunCharts from "../components/RunCharts";
import useDashboardData from "../hooks/useDashboardData";
export default function DecisionsPage() {
  const data = useDashboardData();
  return <DashboardLayout {...data} statusLabel={data.errors.decisions ? "Connection issue" : "Live decision log"} onRefresh={data.refresh} onRun={data.startRun}>
    <section className="page-heading"><p className="eyebrow">RUN INSPECTION</p><h2>Decision log</h2><p>Inspect the latest activity, then review every recorded action and its scheduler state.</p></section>
    <RunCharts decisions={data.decisions} />
    <OrbitalTimeline decisions={data.decisions} loading={data.loading} />
    <section className="full-decision-log"><DecisionFeed decisions={data.decisions} loading={data.loading} /></section>
  </DashboardLayout>;
}
