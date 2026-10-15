import DashboardLayout from "../components/DashboardLayout";
import DecisionFeed from "../components/DecisionFeed";
import FlapHeadingText from "../components/FlapHeadingText";
import useDashboardData from "../hooks/useDashboardData";
export default function DecisionsPage() {
  const data = useDashboardData();
  const preview = data.decisions.some((entry) => entry?.source === "sample_preview");
  const status = data.errors.decisions ? "Connection issue" : preview ? "Sample preview" : `${data.decisions.length} decisions saved`;
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun}>
    <section className="page-heading"><p className="eyebrow">RUN INSPECTION</p><h2 className="page-flap-heading"><FlapHeadingText>Decision log</FlapHeadingText></h2><p>Open a recorded decision to see what the agent observed, chose, and changed in the simulator.</p></section>
    <section className="full-decision-log"><DecisionFeed decisions={data.decisions} loading={data.loading} /></section>
  </DashboardLayout>;
}
