import fs from "fs";
import path from "path";

const projectRoot = path.resolve(process.cwd(), "..");
const useExplanationPreview =
  process.env.NODE_ENV !== "production" &&
  process.env.DASHBOARD_USE_EXPLANATION_PREVIEW === "1";
const decisionsPath = path.join(
  projectRoot,
  useExplanationPreview ? "decision_log.explanation-preview.json" : "decision_log.json"
);

export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed." });
  }

  try {
    const decisions = JSON.parse(fs.readFileSync(decisionsPath, "utf-8"));
    if (!Array.isArray(decisions)) {
      return res.status(500).json({ error: "Decision log must contain a JSON array." });
    }
    return res.status(200).json(decisions);
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
