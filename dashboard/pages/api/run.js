import { spawn } from "child_process";
import { randomUUID } from "crypto";
import path from "path";
import {
  createLiveDecisionLogPath,
  findModel,
  findPython,
  getActiveDecisionLogPath,
  resolveDecisionLogPath,
  setActiveDecisionLogPath,
} from "../../lib/projectFiles";

// Keep state on the server global so Next.js development hot reloads do not
// reset live progress while the child simulator process is still running.
const CURRENT_RUN_KEY = "__auditAgentDashboardCurrentRun";
const MAX_OUTPUT_LENGTH = 4000;
const RUN_TIMEOUT_MS = 10 * 60 * 1000;
const LIVE_DECISIONS = 15;

function explanationSettings() {
  const provider = (process.env.EXPLANATION_PROVIDER || "offline").trim().toLowerCase();
  const hasKey = provider === "gemini"
    ? Boolean(process.env.GEMINI_API_KEY)
    : provider === "claude"
      ? Boolean(process.env.ANTHROPIC_API_KEY)
      : false;
  return {
    explanationProvider: provider,
    explanationReady: provider !== "offline" && hasKey,
  };
}

function publicRunState(projectRoot) {
  const currentRun = globalThis[CURRENT_RUN_KEY];
  const modelPath = findModel(projectRoot);
  const modelAvailable = Boolean(modelPath);
  if (!currentRun) {
    return {
      status: "idle",
      modelAvailable,
      message: "",
      ...(modelPath ? { modelPath: path.relative(projectRoot, modelPath) } : {}),
      outputPath: path.relative(
        projectRoot,
        getActiveDecisionLogPath(projectRoot) || resolveDecisionLogPath(projectRoot)
      ),
      ...explanationSettings(),
    };
  }
  return {
    modelAvailable,
    id: currentRun.id,
    status: currentRun.status,
    message: currentRun.message,
    ...(currentRun.modelPath ? { modelPath: currentRun.modelPath } : {}),
    ...(currentRun.outputPath ? { outputPath: currentRun.outputPath } : {}),
    decisionsCompleted: currentRun.decisionsCompleted,
    decisionsTotal: currentRun.decisionsTotal,
    explanationsCompleted: currentRun.explanationsCompleted,
    explanationsTotal: currentRun.explanationsTotal,
    ...(currentRun.explanationProvider
      ? {
          explanationProvider: currentRun.explanationProvider,
          explanationReady: currentRun.explanationReady,
        }
      : {}),
    ...(currentRun.latestAction ? { latestAction: currentRun.latestAction } : {}),
    ...(currentRun.latestSimulationTime !== undefined
      ? { latestSimulationTime: currentRun.latestSimulationTime }
      : {}),
    ...(currentRun.latestExplanationStatus
      ? { latestExplanationStatus: currentRun.latestExplanationStatus }
      : {}),
    ...(currentRun.detail ? { detail: currentRun.detail } : {}),
    ...(currentRun.finishedAt ? { finishedAt: currentRun.finishedAt } : {}),
  };
}

function appendOutput(run, chunk) {
  run.output = `${run.output}${chunk}`.slice(-MAX_OUTPUT_LENGTH);
}

function handleStdoutLine(run, line) {
  const trimmed = line.trim();
  if (!trimmed) return;
  try {
    const event = JSON.parse(trimmed);
    if (event.type === "decision") {
      setActiveDecisionLogPath(run.projectRoot, run.absoluteOutputPath);
      run.decisionsCompleted = event.index;
      run.decisionsTotal = event.total;
      run.latestAction = event.action_name;
      run.latestSimulationTime = event.time;
      run.explanationProvider = event.explanation_provider;
      run.latestExplanationStatus = event.explanation_status;
      return;
    }
    if (event.type === "complete") {
      run.decisionsCompleted = event.total;
      return;
    }
    if (event.type === "decisions_complete") {
      run.decisionsCompleted = event.total;
      run.message = run.explanationsTotal
        ? "All simulator decisions are saved. Generating optional explanations now."
        : "All simulator decisions are saved.";
      return;
    }
    if (event.type === "explanation") {
      run.explanationsCompleted = event.index;
      run.explanationsTotal = event.total;
      run.latestExplanationStatus = event.explanation_status;
      return;
    }
  } catch {
    // Preserve regular diagnostics without treating them as progress events.
  }
  appendOutput(run, `${line}\n`);
}

function startRun(projectRoot, modelPath) {
  const python = findPython(projectRoot);
  const id = randomUUID();
  const outputPath = createLiveDecisionLogPath(projectRoot, id);
  const settings = explanationSettings();
  const run = {
    id,
    projectRoot,
    absoluteOutputPath: outputPath,
    status: "running",
    message: "The DQN is stepping through simulated processes. Each action appears when that simulator step completes.",
    modelPath: path.relative(projectRoot, modelPath),
    outputPath: path.relative(projectRoot, outputPath),
    output: "",
    decisionsCompleted: 0,
    decisionsTotal: LIVE_DECISIONS,
    explanationsCompleted: 0,
    explanationsTotal: settings.explanationReady ? LIVE_DECISIONS : 0,
    ...settings,
    startedAt: new Date().toISOString(),
  };
  globalThis[CURRENT_RUN_KEY] = run;
  let child;
  try {
    child = spawn(
      python,
      [
        "-m",
        "rl_agent.generate_decision_log",
        "--model-path",
        modelPath,
        "--decisions",
        String(LIVE_DECISIONS),
        "--seed",
        "42",
        "--output",
        outputPath,
        "--stream-jsonl",
        "--step-delay-ms",
        "700",
      ],
      { cwd: projectRoot, env: process.env, stdio: ["ignore", "pipe", "pipe"] }
    );
  } catch (error) {
    globalThis[CURRENT_RUN_KEY] = {
      ...run,
      status: "failed",
      message: "The scheduler process could not be started.",
      detail: error.message,
      finishedAt: new Date().toISOString(),
    };
    return;
  }

  let stdoutBuffer = "";
  child.stdout.on("data", (chunk) => {
    stdoutBuffer += chunk.toString();
    const lines = stdoutBuffer.split(/\r?\n/);
    stdoutBuffer = lines.pop() || "";
    lines.forEach((line) => handleStdoutLine(run, line));
  });
  child.stderr.on("data", (chunk) => appendOutput(run, chunk.toString()));

  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    child.kill("SIGTERM");
  }, RUN_TIMEOUT_MS);

  child.on("error", (error) => {
    clearTimeout(timeout);
    if (globalThis[CURRENT_RUN_KEY]?.id !== run.id) return;
    globalThis[CURRENT_RUN_KEY] = {
      ...run,
      status: "failed",
      message: "The scheduler process could not be started.",
      detail: error.message,
      finishedAt: new Date().toISOString(),
    };
  });

  child.on("close", (code, signal) => {
    clearTimeout(timeout);
    if (globalThis[CURRENT_RUN_KEY]?.id !== run.id) return;
    if (stdoutBuffer.trim()) handleStdoutLine(run, stdoutBuffer);
    const succeeded = code === 0 && !timedOut;
    const outputDetail = run.output.trim().slice(-1200);
    globalThis[CURRENT_RUN_KEY] = {
      ...run,
      status: succeeded ? "succeeded" : "failed",
      message: succeeded
        ? `The live simulator run finished with ${run.decisionsCompleted} recorded agent decisions.`
        : timedOut
          ? `The scheduler run timed out after 10 minutes with ${run.decisionsCompleted} decisions saved; prior run files remain untouched.`
          : `The scheduler run failed after ${run.decisionsCompleted} decisions; prior run files remain untouched.`,
      ...(succeeded || !outputDetail
        ? {}
        : { detail: outputDetail || `Process exited with code ${code ?? signal ?? "unknown"}.` }),
      finishedAt: new Date().toISOString(),
      latestAction: run.latestAction,
      latestSimulationTime: run.latestSimulationTime,
      latestExplanationStatus: run.latestExplanationStatus,
    };
  });
}

export default async function handler(req, res) {
  const modelApiUrl = (process.env.SCHEDULER_MODEL_API_URL || "").replace(/\\/+$/, "");
  if (modelApiUrl) {
    if (req.method === "GET") {
      try {
        const response = await fetch(`${modelApiUrl}/api/run`, { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok) {
          return res.status(response.status).json({
            status: payload.status || "model_missing",
            modelAvailable: false,
            message: payload.error || "The hosted trained model is unavailable.",
          });
        }
        res.setHeader("Cache-Control", "no-store");
        return res.status(200).json({
          status: "idle",
          modelAvailable: true,
          modelPath: payload.modelPath || "rl_agent/policy.json",
          outputPath: "This browser's saved run history",
          message: "",
          ...explanationSettings(),
        });
      } catch (error) {
        return res.status(503).json({
          status: "failed",
          modelAvailable: false,
          message: "Could not reach the hosted scheduler model.",
          detail: error.message,
        });
      }
    }
    if (req.method === "POST") {
      try {
        const response = await fetch(`${modelApiUrl}/api/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ seed: 42, decisions: LIVE_DECISIONS }),
        });
        const payload = await response.json();
        return res.status(response.status).json(payload);
      } catch (error) {
        return res.status(502).json({
          status: "failed",
          modelAvailable: false,
          message: "Could not contact the hosted scheduler model.",
          detail: error.message,
        });
      }
    }
    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({ error: "Method not allowed." });
  }
  if (req.method === "GET") {
    res.setHeader("Cache-Control", "no-store");
    const projectRoot = path.resolve(process.cwd(), "..");
    return res.status(200).json(publicRunState(projectRoot));
  }

  if (req.method !== "POST") {
    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({ error: "Method not allowed." });
  }

  if (globalThis[CURRENT_RUN_KEY]?.status === "running") {
    return res.status(409).json({
      status: "running",
      message: "A scheduler run is already in progress.",
    });
  }

  const projectRoot = path.resolve(process.cwd(), "..");
  const modelPath = findModel(projectRoot);
  if (!modelPath) {
    globalThis[CURRENT_RUN_KEY] = {
      status: "model_missing",
      message:
        "No trained model was found. The dashboard checks the configured model path, then saved seed-42 and seed-123 checkpoints, then a model in the project root. The existing decision log was not changed.",
      finishedAt: new Date().toISOString(),
    };
    return res.status(409).json({
      status: "model_missing",
      message: globalThis[CURRENT_RUN_KEY].message,
      modelAvailable: false,
    });
  }

  startRun(projectRoot, modelPath);
  res.setHeader("Cache-Control", "no-store");
  return res.status(202).json(publicRunState(projectRoot));
}
