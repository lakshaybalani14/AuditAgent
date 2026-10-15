import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/decisions", label: "Decision log" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/evaluation", label: "Evaluation" },
];

export default function DashboardLayout({ children, statusLabel, loading, lastUpdated, errors = {}, runStatus, onRefresh, onRun }) {
  const router = useRouter();
  const [darkMode, setDarkMode] = useState(true);
  const errorText = Object.values(errors).filter(Boolean).join(" ");
  const running = runStatus?.status === "running";
  const time = lastUpdated?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) || "—";

  return (
    <main className={darkMode ? "app-shell dark" : "app-shell"}>
      <div className="app-frame">
        <header className="topbar">
          <Link href="/" className="brand" aria-label="Agentic Scheduler overview">
            <div className="brand-mark"><span /></div>
            <div><p className="eyebrow">SYSTEM INTELLIGENCE</p><h1>Agentic Scheduler</h1></div>
          </Link>
          <nav className="page-nav" aria-label="Dashboard pages">
            {NAV_ITEMS.map((item) => <Link key={item.href} href={item.href} className={router.pathname === item.href ? "page-nav-link active" : "page-nav-link"} aria-current={router.pathname === item.href ? "page" : undefined}>{item.label}</Link>)}
          </nav>
          <div className="topbar-actions">
            <span className={errorText ? "status status-error" : "status"}><i />{errorText ? "Connection issue" : statusLabel}</span>
            <button className="run-button" onClick={onRun} disabled={running}>{running ? "Running…" : "Run scheduler"}</button>
            <button className="icon-button" onClick={() => setDarkMode((value) => !value)} aria-label="Toggle colour theme">{darkMode ? "☼" : "◐"}</button>
            <button className="refresh-button" onClick={() => onRefresh()} disabled={loading}><span>{loading ? "Refreshing" : "Refresh"}</span><b>↻</b></button>
          </div>
        </header>
        {runStatus?.message && <div className={runStatus.status === "failed" || runStatus.status === "model_missing" ? "run-feedback run-feedback-error" : "run-feedback"} role="status"><span>{runStatus.message}</span>{runStatus.detail && <details><summary>Run details</summary><pre>{runStatus.detail}</pre></details>}</div>}
        {errorText && <div className="error-banner" role="alert"><span>{errorText}</span><button onClick={() => onRefresh()}>Retry</button></div>}
        <div className="page-refresh-meta"><span>Updated {time}</span><span>Auto refresh every 5 seconds</span></div>
        <div className="route-content" key={router.pathname}>{children}</div>
      </div>
    </main>
  );
}
