import fs from "fs";
import path from "path";
import {
  getActiveDecisionLogPath,
  resolveDecisionLogPath,
} from "../../lib/projectFiles";

const projectRoot = path.resolve(process.cwd(), "..");
const useExplanationPreview =
  process.env.NODE_ENV !== "production" &&
  process.env.DASHBOARD_USE_EXPLANATION_PREVIEW === "1";

function getDecisionsSource() {
  if (useExplanationPreview) {
    return {
      path: path.join(projectRoot, "decision_log.explanation-preview.json"),
      isSample: true,
    };
  }
  const generatedDecisionLog =
    getActiveDecisionLogPath(projectRoot) || resolveDecisionLogPath(projectRoot);
  return fs.existsSync(generatedDecisionLog)
    ? { path: generatedDecisionLog, isSample: false }
    : { path: path.join(projectRoot, "decision_log.json"), isSample: true };
}

export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed." });
  }

  res.setHeader("Cache-Control", "no-store, max-age=0");

  try {
    const source = getDecisionsSource();
    const decisions = JSON.parse(fs.readFileSync(source.path, "utf-8"));
    if (!Array.isArray(decisions)) {
      return res.status(500).json({ error: "Decision log must contain a JSON array." });
    }
    return res.status(200).json(
      source.isSample
        ? decisions.map((decision) => ({ ...decision, source: "sample_preview" }))
        : decisions
    );
  } catch (error) {
    if (error.code === "ENOENT") {
      return res.status(200).json([]);
    }
    if (error instanceof SyntaxError) {
      return res.status(500).json({ error: "Decision log contains invalid JSON." });
    }
    return res.status(500).json({ error: "Could not read the decision log." });
  }
}
