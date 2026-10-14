import { spawn } from "child_process";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";

// This state is intentionally local to the Next.js server process. The
// dashboard's Run API is for local development, not a serverless deployment.
let currentRun = null;
const MAX_OUTPUT_LENGTH = 4000;
const RUN_TIMEOUT_MS = 10 * 60 * 1000;

function publicRunState() {
  if (!currentRun) return { status: "idle", message: "" };
  return {
    id: currentRun.id,
    status: currentRun.status,
    message: currentRun.message,
    ...(currentRun.detail ? { detail: currentRun.detail } : {}),
    ...(currentRun.finishedAt ? { finishedAt: currentRun.finishedAt } : {}),
  };
}

function appendOutput(run, chunk) {
  run.output = `${run.output}${chunk}`.slice(-MAX_OUTPUT_LENGTH);
}

function findModel(projectRoot) {
  const configuredPath = process.env.SCHEDULER_MODEL_PATH;
  const candidates = configuredPath
    ? [path.resolve(projectRoot, configuredPath)]
    : [path.join(projectRoot, "trained_model.zip"), path.join(projectRoot, "trained_model")];

  return candidates.find((candidate) => {
    try {
      const stat = fs.statSync(candidate);
      return stat.isFile() || stat.isDirectory();
    } catch {
      return false;
    }
  });
}

function startRun(projectRoot, modelPath) {
  const run = {
    id: randomUUID(),
    status: "running",
    message: "The scheduler run is in progress.",
    output: "",
    startedAt: new Date().toISOString(),
  };
  currentRun = run;

  const localPython = path.join(projectRoot, ".venv", "bin", "python");
  const python = process.env.PYTHON || (fs.existsSync(localPython) ? localPython : "python3");
  let child;
  try {
    child = spawn(
      python,
      ["-m", "rl_agent.generate_decision_log", "--model-path", modelPath],
      { cwd: projectRoot, env: process.env, stdio: ["ignore", "pipe", "pipe"] }
    );
  } catch (error) {
    currentRun = {
      ...run,
      status: "failed",
      message: "The scheduler process could not be started.",
      detail: error.message,
      finishedAt: new Date().toISOString(),
    };
    return;
  }

  child.stdout.on("data", (chunk) => appendOutput(run, chunk.toString()));
  child.stderr.on("data", (chunk) => appendOutput(run, chunk.toString()));

  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    child.kill("SIGTERM");
  }, RUN_TIMEOUT_MS);

  child.on("error", (error) => {
    clearTimeout(timeout);
    if (currentRun?.id !== run.id) return;
    currentRun = {
      ...run,
      status: "failed",
      message: "The scheduler process could not be started.",
      detail: error.message,
      finishedAt: new Date().toISOString(),
    };
  });

  child.on("close", (code, signal) => {
    clearTimeout(timeout);
    if (currentRun?.id !== run.id) return;
    const succeeded = code === 0 && !timedOut;
    const outputDetail = run.output.trim().slice(-1200);
    currentRun = {
      ...run,
      status: succeeded ? "succeeded" : "failed",
      message: succeeded
        ? "The run finished. The decision timeline has been refreshed."
        : timedOut
          ? "The scheduler run timed out after 10 minutes. The previous decision log was kept."
          : "The scheduler run failed. The previous decision log was kept.",
      ...(succeeded || !outputDetail
        ? {}
        : { detail: outputDetail || `Process exited with code ${code ?? signal ?? "unknown"}.` }),
      finishedAt: new Date().toISOString(),
    };
  });
}

export default function handler(req, res) {
  if (req.method === "GET") {
    res.setHeader("Cache-Control", "no-store");
    return res.status(200).json(publicRunState());
  }

  if (req.method !== "POST") {
    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({ error: "Method not allowed." });
  }

  if (currentRun?.status === "running") {
    return res.status(409).json({
      status: "running",
      message: "A scheduler run is already in progress.",
    });
  }

  const projectRoot = path.resolve(process.cwd(), "..");
  const modelPath = findModel(projectRoot);
  if (!modelPath) {
    currentRun = {
      status: "model_missing",
      message:
        "A trained model is not available yet. Add trained_model.zip (or trained_model) to the project root, then try again. The existing decision log was not changed.",
      finishedAt: new Date().toISOString(),
    };
    return res.status(409).json({
      status: "model_missing",
      message: currentRun.message,
    });
  }

  startRun(projectRoot, modelPath);
  res.setHeader("Cache-Control", "no-store");
  return res.status(202).json(publicRunState());
}
