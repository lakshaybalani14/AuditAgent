import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import DashboardNavbar from "./DashboardNavbar";

export default function DashboardLayout({ children, statusLabel, lastUpdated, errors = {}, runStatus, onRefresh, onRun, showRunControls = false, showRunDetails = false }) {
  const router = useRouter();
  const [darkMode, setDarkMode] = useState(true);
  useEffect(() => {
    try { setDarkMode(window.localStorage.getItem("auditagent-theme") !== "light"); }
    catch { /* The dashboard still works if browser storage is unavailable. */ }
  }, []);
  const toggleTheme = () => {
    const nextDarkMode = !darkMode;
    setDarkMode(nextDarkMode);
    try { window.localStorage.setItem("auditagent-theme", nextDarkMode ? "dark" : "light"); }
    catch { /* Keep the theme choice for this page. */ }
  };
  const errorText = Object.values(errors).filter(Boolean).join(" ");
  const running = runStatus?.status === "running";
  const time = lastUpdated?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) || "—";
  const explanationReady = Boolean(runStatus?.explanationReady);
  const explanationProvider = runStatus?.explanationProvider || "offline";
  const runButtonLabel = running
    ? explaining
      ? `Explaining ${runStatus.explanationsCompleted || 0}/${runStatus.explanationsTotal}`
      : `Running ${runStatus.decisionsCompleted || 0}/${runStatus.decisionsTotal || 15}`
    : "Run live simulation";
  const runFilesAndSettings = <details className="run-feedback-details"><summary>Run files and settings</summary>
    <div className="run-settings-meta">
      <p className={errorText ? "settings-run-status status-error" : "settings-run-status"}><i aria-hidden="true" />{errorText ? "Connection issue" : statusLabel}</p>
      <p>Last updated: <time dateTime={lastUpdated?.toISOString()}>{time}</time></p>
      <p>{running ? "Live refresh every 0.8 seconds" : "Auto refresh every 5 seconds"}</p>
    </div>
    {runStatus?.modelPath && <p>Checkpoint: <code>{runStatus.modelPath}</code></p>}
    {runStatus?.outputPath && <p>Decision log: <code>{runStatus.outputPath}</code></p>}
    {explanationProvider === "gemini" && !explanationReady && <p>Paste your Gemini key into <code>dashboard/.env.local</code>, then restart the dashboard.</p>}
    {explanationProvider === "offline" && <p>Gemini explanations are disabled. Configure them in <code>dashboard/.env.local</code> and restart the dashboard.</p>}
    {runStatus?.detail && <pre>{runStatus.detail}</pre>}
  </details>;

  return (
    <main className={darkMode ? "app-shell dark" : "app-shell"}>
      <div className="app-frame">
        <DashboardNavbar pathname={router.pathname} darkMode={darkMode} onToggleTheme={toggleTheme} onRun={onRun} showRunControls={showRunControls} runStatus={runStatus} runButtonLabel={runButtonLabel} />
        {!showRunDetails && <div className="run-settings-only">{runFilesAndSettings}</div>}
        {errorText && <div className="error-banner" role="alert"><span>{errorText}</span><button onClick={() => onRefresh()}>Retry</button></div>}
        <div className="route-content" key={router.pathname}>{children}</div>
      </div>
    </main>
  );
}
