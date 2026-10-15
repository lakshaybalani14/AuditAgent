import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PipelineIcon from "./PipelineIcon";
import FlapHeadingText from "./FlapHeadingText";

function deriveStages({ decisions, report, reportStatus, runStatus, errors }) {
  const explanationCount = decisions.filter((item) => Boolean(item?.explanation)).length;
  const explanationPending = decisions.some((item) => item?.explanation_status === "pending");
  const explanationUnavailable = decisions.filter((item) => item?.explanation_status === "unavailable").length;
  const sample = decisions.some((item) => item?.source === "sample_preview");
  const modelAvailable = runStatus?.modelAvailable === true;
  const runState = runStatus?.status || "idle";
  return [
    { id:"model", name:"Trained model", glyph:"model", status:errors?.run?"failed":modelAvailable?"passed":"waiting", state:errors?.run?"Could not check":modelAvailable?"Checkpoint found":"No checkpoint found", detail:errors?.run|| (modelAvailable?`Selected checkpoint: ${runStatus?.modelPath || "available in the repository"}. This saved DQN supplies the actions in a live run.`:"Configure SCHEDULER_MODEL_PATH or place a checkpoint in one of the supported run locations. Existing logs remain viewable."), href:"/evaluation", link:"View model results" },
    { id:"run", name:"Simulator run", glyph:"run", status:errors?.run?"failed":runState==="running"?"running":runState==="failed"?"failed":runState==="succeeded"?"passed":modelAvailable?"ready":"waiting", state:errors?.run?"Status unavailable":runState==="running"?`${runStatus?.decisionsCompleted || 0}/${runStatus?.decisionsTotal || 15} decisions`:runState==="succeeded"?"Last run completed":runState==="failed"?"Last run stopped":modelAvailable?"Ready to start":"Waiting for model", detail:errors?.run||runStatus?.message||(modelAvailable?"Use Run live simulation in the header to generate a new local run.":"A run requires a trained model checkpoint.") },
    { id:"decisions", name:"Decision log", glyph:"log", status:errors?.decisions?"failed":decisions.length?(sample?"sample":"passed"):"waiting", state:errors?.decisions?"Could not load":decisions.length?(sample?`${decisions.length} preview records`:`${decisions.length} decisions saved`):"No records yet", detail:"The Decision log shows each recorded model action, its input and before/after simulator state. A stopped run may still have saved partial results; sample records are labeled separately.", href:"/decisions", link:"Open decision log" },
    { id:"explanation", name:"Explanations", glyph:"explain", status:errors?.decisions?"waiting":explanationPending?"running":explanationUnavailable?"failed":explanationCount?"passed":"optional", state:explanationPending?`${runStatus?.explanationsCompleted || 0}/${runStatus?.explanationsTotal || decisions.length} attempted`:explanationUnavailable?`${explanationUnavailable} unavailable${explanationCount ? ` · ${explanationCount} saved` : ""}`:explanationCount?`${explanationCount} saved explanations`:"None saved", detail:explanationUnavailable?"The provider could not explain some recorded actions. Open the Decision log for each status; the DQN decisions remain available.":"Gemini explains an action after the DQN chooses it. Explanations are optional and do not change the simulator or train the model.", href:"/decisions", link:"Inspect explanations" },
    { id:"evaluation", name:"Evaluation", glyph:"evaluation", status:errors?.report?"failed":report?(reportStatus==="sample"?"sample":"passed"):"waiting", state:errors?.report?"Could not load":report?(reportStatus==="sample"?"Preview data only":"Report available"):"No report found", detail:report?"The Evaluation page compares DQN with fixed schedulers using a separate saved report.":"Run model evaluation separately to produce policy and workload comparisons. The live simulation button does not update this report.", href:"/evaluation", link:"Open evaluation" },
  ];
}

const STATUS_LABELS={passed:"Available",running:"Running",ready:"Ready",waiting:"Waiting",optional:"Optional",sample:"Preview",failed:"Error"};

export default function SchedulerPipeline({decisions=[],report,reportStatus,runStatus,errors={},embedded=false}) {
  const stages=deriveStages({decisions,report,reportStatus,runStatus,errors});
  const [selectedId,setSelectedId]=useState("run");
  const pipelineRef = useRef(null);
  const sceneRef = useRef(null);
  const scrollStageRef = useRef(-1);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [scrollMotion, setScrollMotion] = useState(false);
  useEffect(() => {
    const element = pipelineRef.current;
    if (!element) return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = null;
    const update = () => {
      frame = null;
      if (preference.matches) { setScrollMotion(false); return; }
      const rect = element.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;
      if (!sceneRef.current) return;
      const scene = sceneRef.current.getBoundingClientRect();
      const progress = Math.max(0, Math.min(1, !embedded && window.innerWidth > 980
        ? (110 - scene.top) / Math.max(1, scene.height - rect.height)
        : (window.innerHeight * .8 - rect.top) / (rect.height + window.innerHeight * .2)));
      const stageIndex = Math.min(4, Math.floor(progress * 5));
      setScrollMotion(true);
      setScrollProgress(progress);
      if (scrollStageRef.current !== stageIndex) {
        scrollStageRef.current = stageIndex;
        setSelectedId(["model", "run", "decisions", "explanation", "evaluation"][stageIndex]);
      }
    };
    const schedule = () => { if (frame === null) frame = window.requestAnimationFrame(update); };
    const observer = typeof IntersectionObserver !== "undefined" ? new IntersectionObserver(schedule) : null;
    observer?.observe(element);
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    preference.addEventListener("change", schedule);
    schedule();
    return () => {
      observer?.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      preference.removeEventListener("change", schedule);
      if (frame !== null) window.cancelAnimationFrame(frame);
    };
  }, [embedded]);
  const scrollStageIndex = Math.min(stages.length - 1, Math.floor(scrollProgress * stages.length));
  const selected=stages.find((stage)=>stage.id===selectedId)||stages[1];
  return <>
    {!embedded && <section className="pipeline-intro"><p className="eyebrow">SCHEDULER WORKFLOW</p><h2 className="page-flap-heading"><FlapHeadingText>From model to insight</FlapHeadingText></h2><p>See what is ready for a simulator run, what it recorded, and whether a separate evaluation report exists.</p></section>}
    <div ref={sceneRef} className={!embedded ? "pipeline-scroll-scene" : undefined}>
    <section ref={pipelineRef} className={`scheduler-pipeline${scrollMotion ? " pipeline-scroll-motion" : ""}`} aria-label="Scheduler workflow pipeline" style={{ "--workflow-progress": scrollProgress }}>
      <header className="pipeline-runline"><span className="pipeline-run-id"><i aria-hidden="true">⌘</i><strong>LOCAL RUN</strong><b>·</b><code>{runStatus?.id ? runStatus.id.slice(0,7) : runStatus?.status === "running" ? "running" : runStatus?.status === "model_missing" ? "blocked" : runStatus?.status === "failed" ? "failed" : runStatus?.status === "succeeded" ? "complete" : runStatus?.modelAvailable ? "ready" : "waiting"}</code></span></header>
      <div className="pipeline-scroll-guide" aria-hidden="true"><span>Scroll to explore · {stages[scrollStageIndex].name}</span><div><i /></div></div>
      <div className="pipeline-track">{stages.map((stage,index)=><div className={`pipeline-step-wrap${scrollMotion && scrollStageIndex === index ? " scroll-stage-active" : ""}`} key={stage.id} style={{ "--stage-reveal": scrollMotion ? Math.max(0, Math.min(1, scrollProgress * stages.length - index + 1)) : 1, "--connector-progress": Math.max(0, Math.min(1, scrollProgress * stages.length - index)) }}>
        <button type="button" className={`pipeline-step pipeline-${stage.status}${stage.id===selectedId?" selected":""}`} onClick={()=>setSelectedId(stage.id)} aria-pressed={stage.id===selectedId}>
          <PipelineIcon type={stage.glyph}/><strong className="pipeline-step-name">{stage.name}</strong>
          <span className="pipeline-step-state" aria-live="polite"><i aria-hidden="true">{stage.status==="passed"?"✓":stage.status==="running"?"◌":stage.status==="failed"?"!":stage.status==="optional"?"·":stage.status==="sample"?"~":"○"}</i>{stage.state}</span>
        </button>
        {index<stages.length-1&&<span className={`pipeline-connector${stage.status==="passed"?" connector-done":""}${stage.status==="running"?" connector-running":""}`} aria-hidden="true"><i/><span className="pipeline-scroll-packet"/><b>›</b></span>}
      </div>)}</div>
      <div className="pipeline-detail" key={selected.id}><div><p className="eyebrow">STEP {String(stages.findIndex((stage)=>stage.id===selected.id)+1).padStart(2,"0")} · {STATUS_LABELS[selected.status]}</p><h3>{selected.name}</h3><p>{selected.detail}</p>{selected.id==="run"&&runStatus?.detail&&<details className="pipeline-run-details"><summary>Show run details</summary><pre>{runStatus.detail}</pre></details>}</div><div className="pipeline-actions">{selected.href&&<Link href={selected.href} className="pipeline-link">{selected.link} <span aria-hidden="true">→</span></Link>}</div></div>
    </section>
    </div>
    {!embedded && <p className="pipeline-footnote">Each stage reports available files or recorded status. Evaluation is a separate experiment; it does not depend on Gemini explanations.</p>}
  </>;
}
