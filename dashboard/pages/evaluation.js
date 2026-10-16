import DashboardLayout from "../components/DashboardLayout";
import EvaluationReport from "../components/EvaluationReport";
import FlapHeadingText from "../components/FlapHeadingText";
import useDashboardData from "../hooks/useDashboardData";
export default function EvaluationPage() {
  const data = useDashboardData();
  const status = data.errors.report ? "Connection issue" : data.reportStatus === "sample" ? "Sample preview" : data.reportStatus === "available" ? "Report loaded" : "Awaiting report";
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun}>
    <section className="page-heading"><p className="eyebrow">MODEL PERFORMANCE</p><h2 className="page-flap-heading"><FlapHeadingText>Evaluation</FlapHeadingText></h2><p>Compare scheduling policies and inspect held-out workload results.</p></section>
    <EvaluationReport report={data.report} reportStatus={data.reportStatus} reportInfo={data.reportInfo} loading={data.loading} error={data.errors.report} />
  </DashboardLayout>;
}
