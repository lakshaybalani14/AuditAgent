import DashboardLayout from "../components/DashboardLayout";
import SchedulerPipeline from "../components/SchedulerPipeline";
import useDashboardData from "../hooks/useDashboardData";
export default function PipelinePage() {
  const data = useDashboardData();
  const status = data.errors.run ? "Connection issue" : data.runStatus?.status === "running" ? "Run in progress" : data.runStatus?.modelAvailable ? "Model ready" : "Waiting for model";
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun} showRunControls>
    <SchedulerPipeline decisions={data.decisions} report={data.report} reportStatus={data.reportStatus} runStatus={data.runStatus} errors={data.errors} />
  </DashboardLayout>;
}
