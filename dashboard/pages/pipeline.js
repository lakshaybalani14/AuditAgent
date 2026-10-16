import DashboardLayout from "../components/DashboardLayout";
import SchedulerPipeline from "../components/SchedulerPipeline";
import AnimatedContent from "../components/AnimatedContent";
import useDashboardData from "../hooks/useDashboardData";
export default function PipelinePage() {
  const data = useDashboardData();
  const status = data.errors.run ? "Connection issue" : data.runStatus?.status === "running" ? "Run in progress" : data.runStatus?.modelAvailable ? "Model ready" : "Waiting for model";
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun} showRunControls>
    <AnimatedContent distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <SchedulerPipeline decisions={data.decisions} report={data.report} reportStatus={data.reportStatus} runStatus={data.runStatus} errors={data.errors} />
    </AnimatedContent>
  </DashboardLayout>;
}
