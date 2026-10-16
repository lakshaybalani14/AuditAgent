import WorkloadComparison from "./WorkloadComparison";
import PolicyRadarChart from "./PolicyRadarChart";

const POLICY_ORDER = ["DQN", "Round Robin", "Priority", "MLFQ"];

export default function EvaluationReport({ report, reportStatus, reportInfo, loading, error }) {
  if (loading && !report && !error) return <section className="report-state"><p className="eyebrow">EVALUATION REPORT</p><h3>Loading report…</h3><p>Checking for the latest evaluation results.</p></section>;
  if (error && !report) return <section className="report-state report-state-error" role="alert"><p className="eyebrow">EVALUATION REPORT</p><h3>Could not load the report</h3><p>{error}</p><p>The dashboard automatically retries loading this report.</p></section>;
  if (!report) return <section className="report-state"><p className="eyebrow">EVALUATION REPORT</p><h3>No report loaded</h3><p>No saved evaluation report was found for the selected checkpoint. Run <code>python -m rl_agent.evaluate</code> with that model path and an output file, then refresh this page. Live simulation records decisions but does not generate comparison metrics.</p></section>;
  const config = report.configuration || {};
  const entries = Object.entries(report.policies || {}).sort(([a],[b]) => { const ai=POLICY_ORDER.indexOf(a), bi=POLICY_ORDER.indexOf(b); return (ai<0?POLICY_ORDER.length:ai)-(bi<0?POLICY_ORDER.length:bi); });
  if (!entries.length) return <section className="report-state report-state-error"><h3>Report has no policy results</h3><p>The report loaded but contains no policies to compare.</p></section>;
  const allComplete = entries.every(([, result]) => result?.summary?.mean_process_completion_rate === 1);
  return <>
    {reportStatus === "sample" && <div className="sample-report-banner" role="status"><strong>Sample data</strong><span>Illustrative preview only; these are not measured results.</span></div>}
    {reportStatus !== "sample" && reportInfo?.modelMatchesSelection === false && <div className="sample-report-banner" role="status"><strong>Different checkpoint</strong><span>This report evaluates {report.model_path || "an unspecified model"}. The live simulator currently selects {reportInfo.selectedModelPath}. Compare results using the evaluated checkpoint.</span></div>}
    <section className="run-config panel">
      <div className="panel-heading"><div><p className="eyebrow">EXPERIMENT</p><h3>Run configuration</h3></div><span className="feed-count">{report.workload_source || "Workload source unavailable"}</span></div>
      <div className="config-grid">
        <div><span>Evaluated model</span><strong>{report.model_path || "Not recorded"}</strong></div>
        <div><span>Profiles</span><strong>{Array.isArray(config.workload_profiles) ? config.workload_profiles.join(", ") : "Not recorded"}</strong></div>
        <div><span>Episodes per profile</span><strong>{config.episodes_per_profile ?? "—"}</strong></div>
        <div><span>First seed</span><strong>{config.first_seed ?? "—"}</strong></div>
        <div><span>Processes</span><strong>{config.max_processes ?? "—"}</strong></div>
        <div><span>Report created</span><strong>{report.created_at_utc ? new Date(report.created_at_utc).toLocaleString() : "Not recorded"}</strong></div>
      </div>
      <div className="report-provenance">
        <p><strong>Saved evaluation report</strong>{reportInfo?.source && <> · <code>{reportInfo.source}</code></>}</p>
        <p>The page reloads this file automatically. Results change when evaluation is rerun and the report is saved; live simulation does not recalculate these tables.</p>
      </div>
      {report.matched_workload_note && <p className="report-note">{report.matched_workload_note}</p>}
    </section>
    <section className="panel policy-panel">
      <div className="panel-heading"><div><p className="eyebrow">HELD-OUT EVALUATION</p><h3>Policy comparison</h3></div><span className="feed-count">{entries.length} policies</span></div>
      <PolicyRadarChart entries={entries} />
      <p className="report-note">{allComplete ? "Every policy completed 100% of processes in this report. " : "Completion is the fraction of processes that finished. "}Similar CPU use and throughput can occur on matched workloads even when process waiting times differ.</p>
      {report.metrics_note && <p className="report-note">{report.metrics_note}</p>}
    </section>
    <WorkloadComparison entries={entries} configuredProfiles={config.workload_profiles} />
  </>;
}
