import WorkloadComparison from "./WorkloadComparison";
import PolicyRadarChart from "./PolicyRadarChart";
import EvaluationLiveRun from "./EvaluationLiveRun";
import AnimatedContent from "./AnimatedContent";

const POLICY_ORDER = ["DQN", "Round Robin", "Priority", "MLFQ"];
const revealProps = { distance: 100, direction: "vertical", duration: 0.8, ease: "power3.out", blur: 0, stagger: 0.08, threshold: 0.1 };

export default function EvaluationReport({ report, reportStatus, reportInfo, liveRun, runStatus, loading, error }) {
  const liveRunPanel = <EvaluationLiveRun liveRun={liveRun} runStatus={runStatus} />;
  if (loading && !report && !error) return <>{liveRunPanel}<AnimatedContent {...revealProps} as="section" className="report-state"><p className="eyebrow">SAVED POLICY EVALUATION</p><h3>Loading report…</h3><p>Checking for the latest held-out policy comparison.</p></AnimatedContent></>;
  if (error && !report) return <>{liveRunPanel}<AnimatedContent {...revealProps} as="section" className="report-state report-state-error" role="alert"><p className="eyebrow">SAVED POLICY EVALUATION</p><h3>Could not load the report</h3><p>{error}</p><p>The dashboard automatically retries loading this report.</p></AnimatedContent></>;
  if (!report) return <>{liveRunPanel}<AnimatedContent {...revealProps} as="section" className="report-state"><p className="eyebrow">SAVED POLICY EVALUATION</p><h3>No held-out report loaded</h3><p>No saved policy comparison was found for the selected checkpoint. The live simulation summary above is still available. To compare DQN with Round Robin, Priority, and MLFQ, run <code>python -m rl_agent.evaluate</code> with that model path and save the report.</p></AnimatedContent></>;
  const config = report.configuration || {};
  const entries = Object.entries(report.policies || {}).sort(([a],[b]) => { const ai=POLICY_ORDER.indexOf(a), bi=POLICY_ORDER.indexOf(b); return (ai<0?POLICY_ORDER.length:ai)-(bi<0?POLICY_ORDER.length:bi); });
  if (!entries.length) return <>{liveRunPanel}<AnimatedContent {...revealProps} as="section" className="report-state report-state-error"><h3>Report has no policy results</h3><p>The report loaded but contains no policies to compare.</p></AnimatedContent></>;
  const allComplete = entries.every(([, result]) => result?.summary?.mean_process_completion_rate === 1);
  return <>
    {liveRunPanel}
    {reportStatus === "sample" && <AnimatedContent {...revealProps}><div className="sample-report-banner" role="status"><strong>Sample data</strong><span>Illustrative preview only; these are not measured results.</span></div></AnimatedContent>}
    {reportStatus !== "sample" && reportInfo?.modelMatchesSelection === false && <AnimatedContent {...revealProps}><div className="sample-report-banner" role="status"><strong>Different checkpoint</strong><span>This report evaluates {report.model_path || "an unspecified model"}. The live simulator currently selects {reportInfo.selectedModelPath}. Compare results using the evaluated checkpoint.</span></div></AnimatedContent>}
    <AnimatedContent {...revealProps} as="section" className="panel policy-panel">
      <div className="panel-heading"><div><p className="eyebrow">HELD-OUT EVALUATION</p><h3>Policy comparison</h3></div><span className="feed-count">{entries.length} policies</span></div>
      <p className="report-note saved-report-note">Saved held-out comparison{reportInfo?.source ? <> · <code>{reportInfo.source}</code></> : ""}{report.created_at_utc ? <> · updated {new Date(report.created_at_utc).toLocaleString()}</> : ""}. Run <code>rl_agent.evaluate</code> again to refresh this comparison for a new checkpoint.</p>
      <PolicyRadarChart entries={entries} />
      <p className="report-note">{allComplete ? "Every policy completed 100% of processes in this report. " : "Completion is the fraction of processes that finished. "}Similar CPU use and throughput can occur on matched workloads even when process waiting times differ.</p>
      {report.metrics_note && <p className="report-note">{report.metrics_note}</p>}
    </AnimatedContent>
    <WorkloadComparison entries={entries} configuredProfiles={config.workload_profiles} />
  </>;
}
