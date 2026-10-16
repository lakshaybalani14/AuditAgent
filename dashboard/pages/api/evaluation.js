import fs from "fs";
import path from "path";
import {
  findEvaluationReport,
  findModel,
  getActiveDecisionLogPath,
} from "../../lib/projectFiles";
import { summarizeLiveRun } from "../../lib/liveRunMetrics";

const projectRoot = path.resolve(process.cwd(), "..");
const sampleReportPath = path.join(
  process.cwd(),
  "sample-data",
  "evaluation_results.sample.json"
);

function getLatestLiveRun(projectRoot) {
  const sourcePath = getActiveDecisionLogPath(projectRoot);
  if (!sourcePath) return null;
  try {
    const decisions = JSON.parse(fs.readFileSync(sourcePath, "utf-8"));
    return summarizeLiveRun(decisions, {
      source: path.relative(projectRoot, sourcePath),
      updatedAt: fs.statSync(sourcePath).mtime.toISOString(),
    });
  } catch {
    // A missing or unreadable live trace should not prevent the saved report loading.
    return null;
  }
}

export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed." });
  }
  res.setHeader("Cache-Control", "no-store");

  const useSampleReport =
    process.env.NODE_ENV !== "production" &&
    process.env.DASHBOARD_USE_SAMPLE_REPORT === "1";
  const modelPath = findModel(projectRoot);
  const liveRun = getLatestLiveRun(projectRoot);
  const sourcePath = useSampleReport
    ? sampleReportPath
    : findEvaluationReport(projectRoot, modelPath);
  if (!sourcePath) {
    return res.status(200).json({ status: "missing", report: null, liveRun });
  }

  try {
    const report = JSON.parse(fs.readFileSync(sourcePath, "utf-8"));
    if (!report || typeof report !== "object" || !report.policies || Array.isArray(report.policies) || typeof report.policies !== "object" || !Object.keys(report.policies).length) {
      return res.status(500).json({ error: "Evaluation report has an unsupported format." });
    }
    return res.status(200).json({
      status: useSampleReport ? "sample" : "available",
      source: path.relative(projectRoot, sourcePath),
      selectedModelPath: modelPath ? path.relative(projectRoot, modelPath) : null,
      modelMatchesSelection: modelPath && typeof report.model_path === "string"
        ? path.resolve(projectRoot, report.model_path) === path.resolve(modelPath)
        : null,
      liveRun,
      report,
    });
  } catch (error) {
    if (error.code === "ENOENT") {
      return res.status(200).json({ status: "missing", report: null });
    }
    if (error instanceof SyntaxError) {
      return res.status(500).json({ error: "Evaluation report contains invalid JSON." });
    }
    return res.status(500).json({ error: "Could not read the evaluation report." });
  }
}
