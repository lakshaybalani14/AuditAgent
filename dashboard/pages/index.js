import { useCallback, useEffect, useMemo, useState } from "react";
import QueueView from "../components/QueueView";
import DecisionFeed from "../components/DecisionFeed";

export default function Home() {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const loadDecisions = useCallback(async () => {
    setLoading(true);
    try { const response = await fetch("/api/decisions"); const data = await response.json(); setDecisions(Array.isArray(data) ? data : []); setLastUpdated(new Date()); }
    catch { setDecisions([]); } finally { setLoading(false); }
  }, []);
  useEffect(() => { loadDecisions(); }, [loadDecisions]);
  const latestState = decisions.at(-1)?.state || null;
  const interventions = useMemo(() => decisions.filter((entry) => entry.action !== 0).length, [decisions]);
  return <main className={darkMode ? "app-shell dark" : "app-shell"}><div className="app-frame">
    <header className="topbar"><div className="brand"><div className="brand-mark"><span /></div><div><p className="eyebrow">SYSTEM INTELLIGENCE</p><h1>Agentic Scheduler</h1></div></div><div className="topbar-actions"><span className="status"><i /> Model online</span><button className="icon-button" onClick={() => setDarkMode(!darkMode)} aria-label="Toggle colour theme">{darkMode ? "☼" : "◐"}</button><button className="refresh-button" onClick={loadDecisions} disabled={loading}><span>{loading ? "Refreshing" : "Refresh"}</span><b>↻</b></button></div></header>
    <section className="hero"><div><p className="eyebrow">LIVE DECISION MONITOR</p><h2>Scheduling, <em>explained.</em></h2><p className="hero-copy">A DQN agent observes queue pressure and selects the next scheduling intervention.</p></div><div className="run-meta"><span>RUN SNAPSHOT</span><strong>{lastUpdated ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</strong><small>{decisions.length} decisions captured</small></div></section>
    <section className="metric-grid"><div className="metric-card"><span>Queue depth</span><strong>{latestState?.queue_length ?? "—"}</strong><small>active processes</small></div><div className="metric-card"><span>Average wait</span><strong>{latestState ? latestState.avg_wait_time.toFixed(1) : "—"}</strong><small>scheduler ticks</small></div><div className="metric-card"><span>Interventions</span><strong>{interventions}</strong><small>policy decisions</small></div><div className="metric-card"><span>Starvation risk</span><strong className={latestState?.is_starving ? "danger" : "safe"}>{latestState?.is_starving ? "HIGH" : "CLEAR"}</strong><small>current queue health</small></div></section>
    <section className="dashboard-grid"><QueueView state={latestState} decisions={decisions} /><DecisionFeed decisions={decisions} loading={loading} /></section>
  </div></main>;
}
