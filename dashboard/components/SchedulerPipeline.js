import { useState } from "react";
import Link from "next/link";

function deriveStages({ decisions, report, reportStatus, runStatus, errors }) {
  const explanationCount = decisions.filter((item) => Boolean(item?.explanation)).length;
  const sample = decisions.some((item) => item?.source === "sample_preview");
  const modelAvailable = runStatus?.modelAvailable === true;
  const runState = runStatus?.status || "idle";
  return [
    { id:"model", name:"Trained model", glyph:"model", status:errors?.run?"failed":modelAvailable?"passed":"waiting", state:errors?.run?"Could not check":modelAvailable?"Model file detected":"Waiting for teammate’s model", detail:errors?.run|| (modelAvailable?"A trained model file is available to the local Run API.":"The Run API looks for trained_model.zip or trained_model in the project root. Recorded decisions remain viewable while this is missing."), href:"/evaluation", link:"Evaluation status" },
    { id:"run", name:"Scheduler run", glyph:"run", status:errors?.run?"failed":runState==="running"?"running":runState==="failed"?"failed":runState==="succeeded"?"passed":modelAvailable?"ready":"waiting", state:errors?.run?"Status unavailable":runState==="running"?"Running now":runState==="succeeded"?"Last run completed":runState==="failed"?"Run failed":modelAvailable?"Ready to start":"Waiting for model", detail:errors?.run||runStatus?.message||(modelAvailable?"Use Run scheduler in the header to start a fresh run.":"A fresh run needs the trained model. If the file is missing, the existing decision log is preserved.") },
    { id:"decisions", name:"Decision log", glyph:"log", status:errors?.decisions?"failed":decisions.length?(sample?"sample":"passed"):"waiting", state:errors?.decisions?"Could not load":decisions.length?(sample?`${decisions.length} preview records`:`${decisions.length} decisions recorded`):"No records yet", detail:"The complete recorded scheduler actions and their state snapshots are available on the Decision log page. Preview records are identified separately from model runs.", href:"/decisions", link:"Open decision log" },
    { id:"explanation", name:"Explanation", glyph:"explain", status:errors?.decisions?"waiting":explanationCount?"passed":"optional", state:explanationCount?`${explanationCount} saved explanations`:"Optional · none saved", detail:"Gemini explanations are optional. The dashboard keeps decision details available even if no provider is configured or a request fails.", href:"/decisions", link:"Inspect explanations" },
    { id:"evaluation", name:"Evaluation", glyph:"evaluation", status:errors?.report?"failed":report?(reportStatus==="sample"?"sample":"passed"):"waiting", state:errors?.report?"Could not load":report?(reportStatus==="sample"?"Preview data only":"Report available"):"Waiting for evaluation report", detail:report?"Policy comparison and workload profile metrics are available on the Evaluation page.":"Evaluation results are produced by evaluating the trained model across the workload profiles.", href:"/evaluation", link:"Open evaluation" },
  ];
}

const STATUS_LABELS={passed:"Available",running:"Running",ready:"Ready",waiting:"Waiting",optional:"Optional",sample:"Preview",failed:"Error"};
function StageGlyph({type}) {
  const glyphs={
    model:<><path d="M40 18 50 13 60 18 50 24 40 18Z"/><path d="M40 18v11l10 6V24M60 18v11l-10 6"/></>,
    run:<><circle cx="50" cy="22" r="8"/><path d="M50 17v10m-5-5h10"/></>,
    log:<><path d="M43 17h15M43 22h15M43 27h11"/><circle cx="39" cy="17" r="1"/><circle cx="39" cy="22" r="1"/><circle cx="39" cy="27" r="1"/></>,
    explain:<><path d="M50 14v4m-8 2 3 3m10-3-3 3m-7 4h10m-9 4h8"/><path d="M44 25a7 7 0 1 1 12 4l-1 1h-9l-1-1a7 7 0 0 1-1-4Z"/></>,
    evaluation:<><path d="M45 15h10m-7 0v7l-6 10h16l-6-10v-7"/><path d="M45 27h10"/></>,
  };
  return <svg className="pipeline-cube" viewBox="0 0 100 88" aria-hidden="true"><polygon className="cube-face cube-left" points="12,25 50,45 50,82 12,62"/><polygon className="cube-face cube-right" points="50,45 88,25 88,62 50,82"/><polygon className="cube-face cube-top" points="50,5 88,25 50,45 12,25"/><g className="cube-glyph" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{glyphs[type]}</g></svg>;
}

export default function SchedulerPipeline({decisions=[],report,reportStatus,runStatus,errors={}}) {
  const stages=deriveStages({decisions,report,reportStatus,runStatus,errors});
  const [selectedId,setSelectedId]=useState("run");
  const selected=stages.find((stage)=>stage.id===selectedId)||stages[1];
  return <>
    <section className="pipeline-intro"><p className="eyebrow">SCHEDULER WORKFLOW</p><h2>From model to insight</h2><p>Follow the scheduler’s real path from a trained policy to recorded decisions and evaluation.</p></section>
    <section className="scheduler-pipeline" aria-label="Scheduler workflow pipeline">
      <header className="pipeline-runline"><span className="pipeline-run-id"><i aria-hidden="true">⌘</i><strong>LOCAL RUN</strong><b>·</b><code>{runStatus?.id ? runStatus.id.slice(0,7) : runStatus?.status === "running" ? "running" : runStatus?.status === "model_missing" ? "blocked" : runStatus?.status === "failed" ? "failed" : runStatus?.status === "succeeded" ? "complete" : runStatus?.modelAvailable ? "ready" : "waiting"}</code></span></header>
      <div className="pipeline-track">{stages.map((stage,index)=><div className="pipeline-step-wrap" key={stage.id}>
        <button type="button" className={`pipeline-step pipeline-${stage.status}${stage.id===selectedId?" selected":""}`} onClick={()=>setSelectedId(stage.id)} aria-pressed={stage.id===selectedId}>
          <StageGlyph type={stage.glyph}/><strong className="pipeline-step-name">{stage.name}</strong>
          <span className="pipeline-step-state" aria-live="polite"><i aria-hidden="true">{stage.status==="passed"?"✓":stage.status==="running"?"◌":stage.status==="failed"?"!":stage.status==="optional"?"·":stage.status==="sample"?"~":"○"}</i>{stage.state}</span>
        </button>
        {index<stages.length-1&&<span className={`pipeline-connector${stage.status==="passed"?" connector-done":""}${stage.status==="running"?" connector-running":""}`} aria-hidden="true"><i/><b>›</b></span>}
      </div>)}</div>
      <div className="pipeline-detail" key={selected.id}><div><p className="eyebrow">STEP {String(stages.findIndex((stage)=>stage.id===selected.id)+1).padStart(2,"0")} · {STATUS_LABELS[selected.status]}</p><h3>{selected.name}</h3><p>{selected.detail}</p>{selected.id==="run"&&runStatus?.detail&&<details className="pipeline-run-details"><summary>Show run details</summary><pre>{runStatus.detail}</pre></details>}</div><div className="pipeline-actions">{selected.href&&<Link href={selected.href} className="pipeline-link">{selected.link} <span aria-hidden="true">→</span></Link>}</div></div>
    </section>
    <p className="pipeline-footnote">This view reports files and records the dashboard can verify. It does not invent run durations or treat preview data as evaluation results.</p>
  </>;
}
