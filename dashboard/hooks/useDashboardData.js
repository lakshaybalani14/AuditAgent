import { useCallback, useEffect, useState } from "react";

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
  const [decisions, setDecisions] = useState([]);
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
      if (Array.isArray(results[0].value)) setDecisions(results[0].value);
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
      if (payload && typeof payload === "object" && typeof payload.status === "string") setRunStatus(payload);
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

  return { decisions, report, reportStatus, reportInfo, loading, lastUpdated, errors, runStatus, refresh, startRun };
}
