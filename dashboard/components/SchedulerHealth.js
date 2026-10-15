import AnimatedNumber from "./AnimatedNumber";

export default function SchedulerHealth({ state, interventions = 0 }) {
  return <section className="scheduler-health" aria-labelledby="scheduler-health-title">
    <div className="health-heading"><h3 id="scheduler-health-title">Scheduler health</h3><p>After the latest recorded action</p></div>
    <div className="health-card-grid">
      <article className="health-card"><span>Ready queue depth</span><strong><AnimatedNumber value={state?.queue_length} /></strong><small>processes ready to run</small></article>
      <article className="health-card"><span>Average queue age</span><strong><AnimatedNumber value={state?.avg_wait_time} digits={1} /></strong><small>ticks in ready queue</small></article>
      <article className="health-card"><span>Switch or boost choices</span><strong><AnimatedNumber value={interventions} /></strong><small>actions selected by the agent</small></article>
      <article className={`health-card health-risk${state?.is_starving ? " has-risk" : ""}`}><span>Starvation risk</span><strong className={state?.is_starving ? "danger" : "safe"}>{state ? state.is_starving ? "HIGH" : "CLEAR" : "—"}</strong><small><i aria-hidden="true" />{state ? state.is_starving ? "Waiting threshold exceeded" : "No current starvation signal" : "Awaiting simulator state"}</small></article>
    </div>
  </section>;
}
