import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { summarizeLiveRun } from "../lib/liveRunMetrics";

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`${url} returned an unreadable response.`);
  }
  if (!response.ok) throw new Error(data?.error || `Could not load ${url}.`);
  return data;
}

export default function useDashboardData() {
  const clientRunDecisions = useRef(false);
  const [decisions, setDecisions] = useState([]);

  useEffect(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem("auditagent:last-run") || "null");
      if (Array.isArray(saved) && saved.length) {
        clientRunDecisions.current = true;
        setDecisions(saved);
      }
    } catch {
      window.localStorage.removeItem("auditagent:last-run");
    }
  }, []);
  const [report, setReport] = useState(null);
  const [reportStatus, setReportStatus] = useState("loading");
  const [reportInfo, setReportInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [errors, setErrors] = useState({});
  const [runStatus, setRunStatus] = useState({ status: "idle", message: "" });

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    const results = await Promise.allSettled([
      getJson("/api/decisions"),
      getJson("/api/evaluation"),
      getJson("/api/run"),
    ]);
    const nextErrors = {};
    if (results[0].status === "fulfilled") {
      if (Array.isArray(results[0].value)) {
        const serverHasRun = results[0].value.some((decision) => decision.source !== "sample_preview");
        if (!clientRunDecisions.current || serverHasRun) setDecisions(results[0].value);
      }
      else nextErrors.decisions = "The decision log returned an unexpected format.";
    } else nextErrors.decisions = results[0].reason?.message || "Could not load the decision log.";
    if (results[1].status === "fulfilled") {
      const payload = results[1].value;
      if (payload && typeof payload === "object" && typeof payload.status === "string" && (payload.report === null || (payload.report && typeof payload.report === "object"))) {
        setReport(payload.report);
        setReportStatus(payload.status);
        setReportInfo({ source: payload.source, selectedModelPath: payload.selectedModelPath, modelMatchesSelection: payload.modelMatchesSelection });
      } else nextErrors.report = "The evaluation API returned an unexpected format.";
    } else nextErrors.report = results[1].reason?.message || "Could not load the evaluation report.";
    if (results[2].status === "fulfilled") {
      const payload = results[2].value;
      if (payload && typeof payload === "object" && typeof payload.status === "string") {
        setRunStatus((current) => {
          // The hosted model endpoint reports readiness, not the result of the
          // browser's POST run. Keep the POST result (or error) while polling.
          if (["idle", "ready"].includes(payload.status) && current.status !== "idle") return current;
          return payload;
        });
      }
      else nextErrors.run = "The Run API returned an unexpected format.";
    } else nextErrors.run = results[2].reason?.message || "Could not load scheduler run status.";
    setErrors(nextErrors);
    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  const startRun = useCallback(async () => {
    setRunStatus({ status: "running", message: "Starting the scheduler run…" });
    try {
      const response = await fetch("/api/run", { method: "POST" });
      let result;
      try { result = await response.json(); }
      catch { throw new Error("The Run API returned an unreadable response."); }
      if (!response.ok && response.status !== 409) throw new Error(result.error || result.message || "The scheduler run could not start.");
      if (Array.isArray(result.decisions)) {
        clientRunDecisions.current = true;
        setDecisions(result.decisions);
        window.localStorage.setItem("auditagent:last-run", JSON.stringify(result.decisions));
      }
      setRunStatus(result);
    } catch (error) {
      setRunStatus({ status: "failed", message: error.message || "Could not contact the Run API. Check that the dashboard server is running, then try again." });
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = window.setInterval(() => refresh({ quiet: true }), runStatus.status === "running" ? 800 : 5000);
    return () => window.clearInterval(interval);
  }, [refresh, runStatus.status]);

  const liveRun = useMemo(() => {
    if (!decisions.length || decisions.some((decision) => decision?.source === "sample_preview")) return null;
    return summarizeLiveRun(decisions, {
      source: runStatus?.id ? `auditagent.live-${runStatus.id}` : null,
      updatedAt: lastUpdated?.toISOString?.() || null,
    });
  }, [decisions, lastUpdated, runStatus?.id]);

  return { decisions, report, reportStatus, reportInfo, liveRun, loading, lastUpdated, errors, runStatus, refresh, startRun };
}

