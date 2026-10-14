# Synthetic Workload Profiles

Workload profiles generate seeded process batches for SimulatorCore and RL training. Each profile controls arrival times, CPU bursts, I/O-bound mix, and I/O request events.

## Profiles

| Name | Process mix |
|---|---|
| legacy_random | Original distribution: arrival 0–20, burst 2–15, and 30% I/O-bound processes |
| light_load | Short bursts and arrivals spread across a longer window |
| bursty_arrivals | Most arrivals fall in ticks 0–2, with a smaller burst at ticks 15–20 |
| cpu_heavy | Bursts 10–25 and mostly CPU-bound processes |
| short_job_heavy | Bursts 1–4 |
| io_heavy | 80% I/O-bound processes and bursts 2–12 |
| long_job_heavy | Bursts 16–30 |

For I/O-bound processes with a CPU burst longer than one tick, the generator adds a seeded I/O request before completion. The simulator blocks the process for the generated I/O duration, then returns it to the ready queue. This is a simplified synthetic model, not a trace-calibrated workload.

## Generator contract

`simulator/workload_profiles.py` exposes `PROFILE_NAMES`, `PROFILE_DESCRIPTIONS`, `normalize_workload_profiles(value)`, and `generate_process_specs(profile_name, count, rng)`. The generator returns dictionaries matching Process constructor fields, including `io_requests`. The caller supplies the RNG so the same profile and seed reproduce the same process batch.

## Simulator integration

`SimulatorCore.reset(seed=None, options=None)` accepts an optional `options["workload_profile"]`. When present, the simulator generates that profile. When absent, the constructor-selected scenario remains in use for backward compatibility. A supplied seed restarts the simulator's local random stream; without one, the existing stream continues. Generated processes are sorted by arrival time before arrivals are admitted.

`SchedulerEnv.reset` passes the episode seed and selected profile through to the simulator. It samples uniformly from configured profiles when the reset options do not specify one. Reset info and each step's info include the active profile.

## Training and evaluation

Training chooses uniformly from configured profiles on each episode reset and records the selected profile in the Monitor CSV and training metadata.

~~~bash
python -m rl_agent.train --timesteps 50000 --seed 123 --workload-profiles all --output-dir runs/profile-training
~~~

Evaluation uses the same profile and episode seeds for every policy. Use a separate seed range from training so the comparison covers held-out workloads.

~~~bash
python -m rl_agent.evaluate --model-path runs/profile-training/trained_model.zip --episodes 30 --seed 9000 --workload-profiles all --output runs/profile-training/held-out-evaluation.json
~~~

`episodes` is the number of episodes per profile. The report includes aggregate policy metrics and a summary for each profile. Queue-age metrics are ready-queue samples, not completed-process total waiting times. Person 1's simulator implements distinct MLFQ queues, demotion, and periodic boosts.

