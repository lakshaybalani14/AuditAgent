import { useMemo } from "react";
import DashboardLayout from "../components/DashboardLayout";
import QueueView from "../components/QueueView";
import OrbitalTimeline from "../components/OrbitalTimeline";
import RunCharts from "../components/RunCharts";
import SchedulerPipeline from "../components/SchedulerPipeline";
import SchedulerHealth from "../components/SchedulerHealth";
import FlapHeadingText from "../components/FlapHeadingText";
import AnimatedContent from "../components/AnimatedContent";
import useDashboardData from "../hooks/useDashboardData";
export default function Overview() {
  const data = useDashboardData();
  const latestDecision = data.decisions.at(-1);
  const latestState = latestDecision?.resulting_state || latestDecision?.state || null;
  const interventions = useMemo(() => data.decisions.filter((item) => item.action !== 0).length,[data.decisions]);
  const settingsError = Object.values(data.errors || {}).filter(Boolean).join(" ");
  return <DashboardLayout {...data} onRefresh={data.refresh} onRun={data.startRun} showRunControls>
    <AnimatedContent as="section" className="hero" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <div>
        <p className="eyebrow">SCHEDULER RUN MONITOR</p>
        <h2 className="hero-flap-heading"><FlapHeadingText accentLastWord>Scheduling, explained.</FlapHeadingText></h2>
        <p className="hero-copy">Watch the trained agent choose scheduler actions for simulated processes.</p>
      </div>
      <div className="run-meta">
        <span>RECORDED DECISIONS</span>
        <strong>{data.decisions.length}</strong>
        <small>{latestDecision?.source === "sample_preview" ? "Sample preview" : "From the active decision log"}</small>
        <details className="run-feedback-details overview-run-settings">
          <summary>Run files and settings</summary>
          <div className="run-trace-settings">
            <p>Last updated: <time dateTime={data.lastUpdated?.toISOString?.()}>{data.lastUpdated?.toLocaleTimeString?.([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) || "—"}</time></p>
            <p>{data.runStatus?.status === "running" ? "Live refresh every 0.8 seconds" : "Auto refresh every 5 seconds"}</p>
            {settingsError && <p className="settings-run-status status-error"><i aria-hidden="true" />Connection issue: {settingsError}</p>}
            {data.runStatus?.modelPath && <p>Checkpoint: <code>{data.runStatus.modelPath}</code></p>}
            {data.runStatus?.outputPath && <p>Decision log: <code>{data.runStatus.outputPath}</code></p>}
            {data.runStatus?.explanationProvider === "gemini" && !data.runStatus?.explanationReady && <p>Gemini explanations are unavailable for this session. Check the dashboard API key configuration.</p>}
            {data.runStatus?.explanationProvider === "offline" && <p>Gemini explanations are disabled for this run.</p>}
            {data.runStatus?.detail && <pre>{data.runStatus.detail}</pre>}
          </div>
        </details>
      </div>
    </AnimatedContent>
    <AnimatedContent as="section" className="page-section overview-pipeline" aria-labelledby="overview-pipeline-heading" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <div className="section-heading"><div><p className="eyebrow">01 · WORKFLOW</p><h3 id="overview-pipeline-heading"><FlapHeadingText>Pipeline demonstration</FlapHeadingText></h3></div></div>
      <SchedulerPipeline decisions={data.decisions} report={data.report} reportStatus={data.reportStatus} runStatus={data.runStatus} errors={data.errors} embedded />
    </AnimatedContent>
    <AnimatedContent as="section" className="page-section overview-run-grid" aria-label="Scheduler health and agent decisions" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <p className="eyebrow overview-section-index">02 · LIVE SCHEDULER</p>
      <SchedulerHealth state={latestState} interventions={interventions} />
      <RunCharts decisions={data.decisions} />
    </AnimatedContent>
    <AnimatedContent as="section" className="page-section" aria-labelledby="process-heading" distance={100} direction="vertical" duration={0.8} ease="power3.out" blur={0} stagger={0.08} threshold={0.1}>
      <div className="section-heading process-section-heading"><div><p className="eyebrow">03 · PROCESS VIEW</p><h3 id="process-heading"><FlapHeadingText>Processes and recent choices</FlapHeadingText></h3></div><div className="agent-activity-heading"><div className="agent-activity-title-row"><h3><FlapHeadingText>Agent activity</FlapHeadingText></h3><span className="feed-count">Latest {Math.min(8, data.decisions.length)} / {data.decisions.length}</span></div><p>Click the orbital to view the step.</p></div></div>
      <div className="dashboard-grid"><QueueView state={latestState} decisions={data.decisions} /><OrbitalTimeline decisions={data.decisions} loading={data.loading} runStatus={data.runStatus} /></div>
    </AnimatedContent>
  </DashboardLayout>;
}
