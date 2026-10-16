import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import DashboardNavbar from "./DashboardNavbar";

export default function DashboardLayout({ children, errors = {}, runStatus, onRefresh, onRun, showRunControls = false }) {
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
  const explaining = running && runStatus?.decisionsCompleted >= runStatus?.decisionsTotal && runStatus?.explanationsTotal > 0;
  const runButtonLabel = running
    ? explaining
      ? `Explaining ${runStatus.explanationsCompleted || 0}/${runStatus.explanationsTotal}`
      : `Running ${runStatus.decisionsCompleted || 0}/${runStatus.decisionsTotal || 15}`
    : "Run live simulation";
  return (
    <main className={`${darkMode ? "app-shell dark" : "app-shell"}${router.pathname === "/" ? " overview-shell" : ""}`}>
      <div className="app-frame">
        <DashboardNavbar pathname={router.pathname} darkMode={darkMode} onToggleTheme={toggleTheme} onRun={onRun} showRunControls={showRunControls} runStatus={runStatus} runButtonLabel={runButtonLabel} />
        {errorText && <div className="error-banner" role="alert"><span>{errorText}</span><button onClick={() => onRefresh()}>Retry</button></div>}
        <div className="route-content" key={router.pathname}>{children}</div>
      </div>
    </main>
  );
}
