import DashboardLayout from "../components/DashboardLayout";
import DecisionFeed from "../components/DecisionFeed";
import FlapHeadingText from "../components/FlapHeadingText";
import AnimatedContent from "../components/AnimatedContent";
import useDashboardData from "../hooks/useDashboardData";
export default function DecisionsPage() {
  const data = useDashboardData();
  const preview = data.decisions.some((entry) => entry?.source === "sample_preview");
  const status = data.errors.decisions ? "Connection issue" : preview ? "Sample preview" : `${data.decisions.length} decisions saved`;
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun}>
    <AnimatedContent as="section" className="page-heading" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <h2 className="page-flap-heading"><FlapHeadingText>Decision log</FlapHeadingText></h2>
      <p>Open a recorded decision to see what the agent observed, chose, and changed in the simulator.</p>
    </AnimatedContent>
    <AnimatedContent as="section" className="full-decision-log" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <DecisionFeed decisions={data.decisions} loading={data.loading} />
    </AnimatedContent>
  </DashboardLayout>;
}
