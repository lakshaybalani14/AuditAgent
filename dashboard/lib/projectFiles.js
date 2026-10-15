import fs from "fs";
import path from "path";

const DEFAULT_MODELS = [
  path.join("runs", "dqn-learning-v2-seed-42", "best_model.zip"),
  path.join("runs", "dqn-learning-v2-seed-123-switch-1", "best_model.zip"),
  "trained_model.zip",
  "trained_model",
];

export function findModel(projectRoot) {
  const configuredPath = process.env.SCHEDULER_MODEL_PATH;
  const candidates = configuredPath
    ? [path.resolve(projectRoot, configuredPath)]
    : DEFAULT_MODELS.map((candidate) => path.join(projectRoot, candidate));

  return candidates.find((candidate) => {
    try {
      const stat = fs.statSync(candidate);
      return stat.isFile() || stat.isDirectory();
    } catch {
      return false;
    }
  });
}

export function resolveDecisionLogPath(projectRoot) {
  return process.env.SCHEDULER_DECISION_LOG_PATH
    ? path.resolve(projectRoot, process.env.SCHEDULER_DECISION_LOG_PATH)
    : path.join(projectRoot, "decision_log.generated.json");
}

export function createLiveDecisionLogPath(projectRoot, runId) {
  const configuredPath = resolveDecisionLogPath(projectRoot);
  const extension = path.extname(configuredPath) || ".json";
  const name = path.basename(configuredPath, extension);
  return path.join(
    path.dirname(configuredPath),
    `${name}.live-${runId}${extension}`
  );
}

const ACTIVE_LOG_STATE_DIR = ".dashboard-data";
const ACTIVE_LOG_POINTER = "active-decision-log.json";

export function setActiveDecisionLogPath(projectRoot, outputPath) {
  const stateDirectory = path.join(projectRoot, ACTIVE_LOG_STATE_DIR);
  fs.mkdirSync(stateDirectory, { recursive: true });
  fs.writeFileSync(
    path.join(stateDirectory, ACTIVE_LOG_POINTER),
    JSON.stringify({ path: path.relative(projectRoot, outputPath) }, null, 2),
    "utf-8"
  );
}

export function getActiveDecisionLogPath(projectRoot) {
  try {
    const pointer = JSON.parse(
      fs.readFileSync(
        path.join(projectRoot, ACTIVE_LOG_STATE_DIR, ACTIVE_LOG_POINTER),
        "utf-8"
      )
    );
    return typeof pointer.path === "string"
      ? path.resolve(projectRoot, pointer.path)
      : null;
  } catch {
    return null;
  }
}

export function findEvaluationReport(projectRoot, modelPath) {
  const configuredPath = process.env.SCHEDULER_EVALUATION_PATH;
  if (configuredPath) return path.resolve(projectRoot, configuredPath);

  const candidates = [];
  if (modelPath) {
    const modelDirectory = path.dirname(modelPath);
    candidates.push(path.join(modelDirectory, "evaluation.json"));
    try {
      const profileReports = fs
        .readdirSync(modelDirectory)
        .filter((name) => /^evaluation.*\.json$/i.test(name) && !/diagnostic/i.test(name))
        .map((name) => path.join(modelDirectory, name))
        .sort((left, right) => fs.statSync(right).mtimeMs - fs.statSync(left).mtimeMs);
      candidates.push(...profileReports);
    } catch {
      // A model may live outside a run directory; try the project report below.
    }
  }
  candidates.push(path.join(projectRoot, "evaluation_results.json"));
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

export function findPython(projectRoot) {
  if (process.env.PYTHON) {
    const configured = process.env.PYTHON;
    return path.isAbsolute(configured) || configured.includes("/") || configured.includes("\\")
      ? path.resolve(projectRoot, configured)
      : configured;
  }

  const localCandidates = process.platform === "win32"
    ? [
        path.join(projectRoot, ".venv", "Scripts", "python.exe"),
        path.join(projectRoot, ".venv", "bin", "python.exe"),
      ]
    : [path.join(projectRoot, ".venv", "bin", "python")];
  const localPython = localCandidates.find((candidate) => fs.existsSync(candidate));
  return localPython || (process.platform === "win32" ? "python" : "python3");
}
