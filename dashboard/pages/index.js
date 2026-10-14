import { useCallback, useEffect, useMemo, useState } from "react";
import QueueView from "../components/QueueView";
import DecisionFeed from "../components/DecisionFeed";

const POLICY_ORDER = ["DQN", "Round Robin", "Priority", "MLFQ"];

function formatMetric(value, digits = 1) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
}

function EvaluationPanel({ report, reportStatus }) {
  if (!report) {
    return (
      <section className="panel report-empty">
        <div>
          <p className="eyebrow">EVALUATION REPORT</p>
          <h3>No report loaded</h3>
          <p>No <code>evaluation_results.json</code> was found in the project root. Evaluation needs the trained model from Person 3. Once <code>trained_model.zip</code> is in the project root, run <code>python -m rl_agent.evaluate --model-path trained_model.zip --workload-profiles all</code>. The dashboard works without a cloud API key.</p>
        </div>
      </section>
    );
  }

  const config = report.configuration || {};
  const policyEntries = Object.entries(report.policies || {}).sort(([a], [b]) => {
    const ai = POLICY_ORDER.indexOf(a);
    const bi = POLICY_ORDER.indexOf(b);
    return (ai < 0 ? POLICY_ORDER.length : ai) - (bi < 0 ? POLICY_ORDER.length : bi);
  });

  return (
    <>
      {reportStatus === "sample" && (
        <div className="sample-report-banner" role="status">
          <strong>Sample data</strong>
          <span>These illustrative values are for dashboard preview only, not measured results.</span>
        </div>
      )}
      <section className="run-config panel">
        <div className="panel-heading">
          <div><p className="eyebrow">EXPERIMENT</p><h3>Run configuration</h3></div>
          <span className="feed-count">{report.workload_source || "Workload source unavailable"}</span>
        </div>
        <div className="config-grid">
          <div><span>Model</span><strong>{report.model_path || "Not recorded"}</strong></div>
          <div><span>Profiles</span><strong>{Array.isArray(config.workload_profiles) ? config.workload_profiles.join(", ") : "Not recorded"}</strong></div>
          <div><span>Episodes per profile</span><strong>{config.episodes_per_profile ?? "—"}</strong></div>
          <div><span>First seed</span><strong>{config.first_seed ?? "—"}</strong></div>
          <div><span>Processes</span><strong>{config.max_processes ?? "—"}</strong></div>
          <div><span>Created</span><strong>{report.created_at_utc ? new Date(report.created_at_utc).toLocaleString() : "Not recorded"}</strong></div>
        </div>
        {report.matched_workload_note && <p className="report-note">{report.matched_workload_note}</p>}
      </section>

      <section className="panel policy-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">HELD-OUT EVALUATION</p><h3>Policy comparison</h3></div>
          <span className="feed-count">{policyEntries.length} policies</span>
        </div>
        <div className="table-wrap">
          <table className="policy-table">
            <thead><tr><th>Policy</th><th>Mean wait</th><th>P95 wait</th><th>Completion</th><th>CPU use</th><th>Throughput</th></tr></thead>
            <tbody>
              {policyEntries.map(([name, result]) => {
                const summary = result?.summary || {};
                return (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    <td>{formatMetric(summary.mean_process_waiting_time_ticks)} ticks</td>
                    <td>{formatMetric(summary.mean_p95_process_waiting_time_ticks)} ticks</td>
                    <td>{formatMetric((summary.mean_process_completion_rate || 0) * 100, 0)}%</td>
                    <td>{formatMetric((summary.mean_cpu_utilization || 0) * 100, 0)}%</td>
                    <td>{formatMetric(summary.mean_throughput_processes_per_tick, 2)}/tick</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {report.metrics_note && <p className="report-note">{report.metrics_note}</p>}
      </section>

      <section className="profile-grid">
        {policyEntries.map(([name, result]) => (
          <article className="panel profile-card" key={name}>
            <div className="panel-heading"><div><p className="eyebrow">BY WORKLOAD PROFILE</p><h3>{name}</h3></div></div>
            {Object.entries(result?.by_profile || {}).length ? (
              <div className="profile-list">
                {Object.entries(result.by_profile).map(([profile, metrics]) => (
                  <div className="profile-row" key={profile}>
                    <strong>{profile.replaceAll("_", " ")}</strong>
                    <span>Wait {formatMetric(metrics.mean_process_waiting_time_ticks)} ticks</span>
                    <span>Complete {formatMetric((metrics.mean_process_completion_rate || 0) * 100, 0)}%</span>
                    <span>CPU {formatMetric((metrics.mean_cpu_utilization || 0) * 100, 0)}%</span>
                  </div>
                ))}
              </div>
            ) : <p className="report-note">This report has no profile-level summaries.</p>}
          </article>
        ))}
      </section>
    </>
  );
}

export default function Home() {
  const [decisions, setDecisions] = useState([]);
  const [report, setReport] = useState(null);
  const [reportStatus, setReportStatus] = useState("loading");
  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState("");
  const [runStatus, setRunStatus] = useState({ status: "idle", message: "" });

  const loadDashboard = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    try {
      const [decisionResponse, reportResponse, runStatusResponse] = await Promise.all([
        fetch("/api/decisions", { cache: "no-store" }),
        fetch("/api/evaluation", { cache: "no-store" }),
        fetch("/api/run", { cache: "no-store" }),
      ]);
      const [decisionData, reportData, runData] = await Promise.all([
        decisionResponse.json(),
        reportResponse.json(),
        runStatusResponse.json(),
      ]);
      if (!decisionResponse.ok) throw new Error(decisionData.error || "Could not load decisions.");
      if (!reportResponse.ok) throw new Error(reportData.error || "Could not load the evaluation report.");
      setDecisions(Array.isArray(decisionData) ? decisionData : []);
      setReport(reportData.report || null);
      setReportStatus(reportData.status || "missing");
      setRunStatus(runData);
      setError("");
      setLastUpdated(new Date());
    } catch (requestError) {
      setError(requestError.message || "Dashboard data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  const startRun = useCallback(async () => {
    setRunStatus({ status: "running", message: "Starting the scheduler run…" });
    try {
      const response = await fetch("/api/run", { method: "POST" });
      const result = await response.json();
      setRunStatus(result);
    } catch {
      setRunStatus({
        status: "failed",
        message: "Could not contact the Run API. Check that the dashboard server is running, then try again.",
      });
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const intervalId = window.setInterval(() => loadDashboard({ quiet: true }), 5000);
    return () => window.clearInterval(intervalId);
  }, [loadDashboard]);

  const latestState = decisions.at(-1)?.state || null;
  const interventions = useMemo(() => decisions.filter((entry) => entry.action !== 0).length, [decisions]);
  const statusLabel = error ? "Connection issue" : loading ? "Loading data" : reportStatus === "sample" ? "Sample preview" : reportStatus === "available" ? "Report loaded" : "Awaiting report";

  return (
    <main className={darkMode ? "app-shell dark" : "app-shell"}>
      <div className="app-frame">
        <header className="topbar">
          <div className="brand"><div className="brand-mark"><span /></div><div><p className="eyebrow">SYSTEM INTELLIGENCE</p><h1>Agentic Scheduler</h1></div></div>
          <div className="topbar-actions">
            <span className={error ? "status status-error" : "status"}><i />{statusLabel}</span>
            <button className="run-button" onClick={startRun} disabled={runStatus.status === "running"}>
              {runStatus.status === "running" ? "Running…" : "Run scheduler"}
            </button>
            <button className="icon-button" onClick={() => setDarkMode(!darkMode)} aria-label="Toggle colour theme">{darkMode ? "☼" : "◐"}</button>
            <button className="refresh-button" onClick={() => loadDashboard()} disabled={loading}><span>{loading ? "Refreshing" : "Refresh"}</span><b>↻</b></button>
          </div>
        </header>

        {runStatus.message && (
          <div className={runStatus.status === "failed" || runStatus.status === "model_missing" ? "run-feedback run-feedback-error" : "run-feedback"} role="status">
            <span>{runStatus.message}</span>
            {runStatus.detail && <details><summary>Run details</summary><pre>{runStatus.detail}</pre></details>}
          </div>
        )}
        {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={() => loadDashboard()}>Retry</button></div>}

        <section className="hero">
          <div><p className="eyebrow">SCHEDULER RUN MONITOR</p><h2>Scheduling, <em>explained.</em></h2><p className="hero-copy">Review the experiment setup, compare scheduling policies, and inspect the agent’s recorded decisions.</p></div>
          <div className="run-meta"><span>LAST REFRESH</span><strong>{lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—"}</strong><small>{decisions.length} decisions · updates every 5 seconds</small></div>
        </section>

        <EvaluationPanel report={report} reportStatus={reportStatus} />

        <section className="metric-grid">
          <div className="metric-card"><span>Latest queue depth</span><strong>{latestState?.queue_length ?? "—"}</strong><small>ready processes</small></div>
          <div className="metric-card"><span>Latest average queue age</span><strong>{latestState ? formatMetric(latestState.avg_wait_time) : "—"}</strong><small>ticks in ready queue</small></div>
          <div className="metric-card"><span>Agent interventions</span><strong>{interventions}</strong><small>non no-change decisions</small></div>
          <div className="metric-card"><span>Latest starvation risk</span><strong className={latestState?.is_starving ? "danger" : "safe"}>{latestState ? latestState.is_starving ? "HIGH" : "CLEAR" : "—"}</strong><small>from the decision log</small></div>
        </section>

        <section className="dashboard-grid"><QueueView state={latestState} decisions={decisions} /><DecisionFeed decisions={decisions} loading={loading} /></section>
      </div>
    </main>
  );
}
