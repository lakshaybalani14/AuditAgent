import DashboardLayout from "../components/DashboardLayout";
import EvaluationReport from "../components/EvaluationReport";
import FlapHeadingText from "../components/FlapHeadingText";
import AnimatedContent from "../components/AnimatedContent";
import useDashboardData from "../hooks/useDashboardData";
export default function EvaluationPage() {
  const data = useDashboardData();
  const status = data.errors.report ? "Connection issue" : data.reportStatus === "sample" ? "Sample preview" : data.reportStatus === "available" ? "Report loaded" : "Awaiting report";
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun}>
    <AnimatedContent as="section" className="page-heading" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <p className="eyebrow">MODEL PERFORMANCE</p>
      <h2 className="page-flap-heading"><FlapHeadingText>Evaluation</FlapHeadingText></h2>
      <p>Compare scheduling policies and inspect held-out workload results.</p>
    </AnimatedContent>
    <EvaluationReport report={data.report} reportStatus={data.reportStatus} reportInfo={data.reportInfo} liveRun={data.liveRun} runStatus={data.runStatus} loading={data.loading} error={data.errors.report} />
  </DashboardLayout>;
}
