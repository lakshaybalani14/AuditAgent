import fs from "fs";
import path from "path";

export default function handler(req, res) {
  const filePath = path.join(process.cwd(), "..", "decision_log.json");

  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const decisions = JSON.parse(raw);
    res.status(200).json(decisions);
  } catch (err) {
    // decision_log.json doesn't exist yet (explainer.py hasn't been run) —
    // render an empty state gracefully instead of crashing.
    res.status(200).json([]);
  }
}
