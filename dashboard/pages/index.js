import { useMemo } from "react";
import Link from "next/link";
import DashboardLayout from "../components/DashboardLayout";
import QueueView from "../components/QueueView";
import OrbitalTimeline from "../components/OrbitalTimeline";
import RunCharts from "../components/RunCharts";
import SchedulerPipeline from "../components/SchedulerPipeline";
import SchedulerHealth from "../components/SchedulerHealth";
import FlapHeadingText from "../components/FlapHeadingText";
import useDashboardData from "../hooks/useDashboardData";
export default function Overview() {
  const data = useDashboardData();
  const latestDecision = data.decisions.at(-1);
  const latestState = latestDecision?.resulting_state || latestDecision?.state || null;
  const interventions = useMemo(() => data.decisions.filter((item) => item.action !== 0).length,[data.decisions]);
  const status = data.runStatus?.status === "running" ? "Simulation running" : data.runStatus?.status === "failed" ? "Last run stopped" : data.runStatus?.modelAvailable ? "Model ready" : "Waiting for model";
  return <DashboardLayout {...data} statusLabel={status} onRefresh={data.refresh} onRun={data.startRun} showRunControls showRunDetails>
    <section className="hero"><div><p className="eyebrow">SCHEDULER RUN MONITOR</p><h2 className="hero-flap-heading"><FlapHeadingText accentLastWord>Scheduling, explained.</FlapHeadingText></h2><p className="hero-copy">Watch the trained agent choose scheduler actions for simulated processes.</p></div><div className="run-meta"><span>RECORDED DECISIONS</span><strong>{data.decisions.length}</strong><small>{latestDecision?.source === "sample_preview" ? "Sample preview" : "From the active decision log"}</small></div></section>
    <section className="page-section overview-pipeline" aria-labelledby="overview-pipeline-heading">
      <div className="section-heading"><div><p className="eyebrow">01 · WORKFLOW</p><h3 id="overview-pipeline-heading"><FlapHeadingText>Pipeline demonstration</FlapHeadingText></h3></div></div>
      <SchedulerPipeline decisions={data.decisions} report={data.report} reportStatus={data.reportStatus} runStatus={data.runStatus} errors={data.errors} embedded />
    </section>
    <section className="page-section overview-run-grid" aria-label="Scheduler health and agent decisions">
      <SchedulerHealth state={latestState} interventions={interventions} />
      <RunCharts decisions={data.decisions} />
    </section>
    <section className="page-section" aria-labelledby="process-heading">
      <div className="section-heading process-section-heading">
        <div><p className="eyebrow">03 · PROCESS VIEW</p><h3 id="process-heading"><FlapHeadingText>Processes and recent choices</FlapHeadingText></h3></div>
        <div className="agent-activity-heading">
          <div className="agent-activity-title-row"><h3><FlapHeadingText>Agent activity</FlapHeadingText></h3><span className="feed-count">Latest {Math.min(8, data.decisions.length)} / {data.decisions.length}</span></div>
          <p>Click the orbital to view the step.</p>
        </div>
      </div>
      <div className="dashboard-grid"><QueueView state={latestState} decisions={data.decisions} /><OrbitalTimeline decisions={data.decisions} loading={data.loading} runStatus={data.runStatus} /></div>
    </section>
    <Link href="/evaluation" className="overview-report-link"><span><b>{data.report ? "Evaluation report ready" : "Evaluation report not available yet"}</b><small>{data.report ? "Open policy comparisons and workload results" : "The Overview and Decision log work while waiting for the trained model"}</small></span><strong>{data.report ? "View evaluation →" : "Why? →"}</strong></Link>
  </DashboardLayout>;
}
