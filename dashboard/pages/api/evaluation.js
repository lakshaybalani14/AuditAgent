import fs from "fs";
import path from "path";
import { findEvaluationReport, findModel } from "../../lib/projectFiles";

const projectRoot = path.resolve(process.cwd(), "..");
const sampleReportPath = path.join(
  process.cwd(),
  "sample-data",
  "evaluation_results.sample.json"
);

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
  const sourcePath = useSampleReport
    ? sampleReportPath
    : findEvaluationReport(projectRoot, modelPath);
  if (!sourcePath) {
    return res.status(200).json({ status: "missing", report: null });
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
