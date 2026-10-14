import fs from "fs";
import path from "path";

const reportPath = path.join(process.cwd(), "..", "evaluation_results.json");
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

  const useSampleReport =
    process.env.NODE_ENV !== "production" &&
    process.env.DASHBOARD_USE_SAMPLE_REPORT === "1";
  const sourcePath = useSampleReport ? sampleReportPath : reportPath;

  try {
    const report = JSON.parse(fs.readFileSync(sourcePath, "utf-8"));
    if (!report || typeof report !== "object" || !report.policies) {
      return res.status(500).json({ error: "Evaluation report has an unsupported format." });
    }
    return res.status(200).json({ status: useSampleReport ? "sample" : "available", report });
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
