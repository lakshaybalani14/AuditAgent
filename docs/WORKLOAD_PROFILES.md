# Synthetic Workload Profiles

This branch adds profile definitions and RL-side selection. It does not change SimulatorCore. Named profiles become runnable after SimulatorCore implements the reset contract below; legacy_random remains compatible with the current simulator.

## Profiles

| Name | Process mix |
|---|---|
| legacy_random | The current distribution: arrival 0–20, burst 2–15, and 30% I/O-bound labels |
| light_load | Short bursts and arrivals spread across a longer window |
| bursty_arrivals | Most arrivals fall in ticks 0–2, with a smaller burst at ticks 15–20 |
| cpu_heavy | Bursts 10–25 and mostly CPU-bound labels |
| short_job_heavy | Bursts 1–4 |
| io_heavy | 80% I/O-bound labels and bursts 2–12 |
| long_job_heavy | Bursts 16–30 |

The current Process model only stores an is_io_bound label; SimulatorCore does not yet model I/O blocking or return from I/O. Therefore io_heavy currently varies the label seen by the observation, not actual CPU/I/O behavior. Do not interpret it as a realistic I/O workload until the simulator models that behavior.

## Generator contract

simulator/workload_profiles.py exposes:

- PROFILE_NAMES and PROFILE_DESCRIPTIONS for validation and documentation.
- normalize_workload_profiles(value) to accept a profile sequence, a comma-separated CLI value, or all.
- generate_process_specs(profile_name, count, rng) to return dictionaries matching Process constructor fields.

The caller supplies an RNG so the same profile and seed can reproduce the same process batch. SimulatorCore should turn each returned dictionary into a Process.

## SimulatorCore integration contract

For named profiles, SimulatorCore.reset should accept the Gymnasium-style signature:

~~~python
reset(seed=None, options=None)
~~~

Read options["workload_profile"], defaulting to legacy_random. When seed is supplied, initialize a local random.Random(seed); otherwise continue using the simulator's existing RNG stream. Call generate_process_specs(profile_name, max_processes, rng), create the Process objects, sort by arrival_time, and then admit arrivals as usual.

SchedulerEnv.reset passes both the episode seed and workload_profile in options. It returns the chosen profile in reset info and includes the profile name in each step's info. The old simulator reset() still works with legacy_random for backward compatibility. Selecting another named profile with an old SimulatorCore raises a clear integration error instead of silently simulating the wrong workload.

## Training and evaluation

Training chooses uniformly from the configured profiles on each episode reset and records the selected profile in the Monitor CSV and training metadata.

Example training run:

~~~bash
python -m rl_agent.train --timesteps 50000 --seed 123 --workload-profiles all --output-dir runs/profile-training
~~~

Evaluate on a separate seed range, with each policy receiving the same profile and episode seeds:

~~~bash
python -m rl_agent.evaluate --model-path runs/profile-training/trained_model.zip --episodes 30 --seed 9000 --workload-profiles all --output runs/profile-training/held-out-evaluation.json
~~~

The episodes setting is the number of episodes per profile. The evaluation report includes aggregate policy metrics and a summary for each workload profile. Use separate training and evaluation seed ranges so the final comparison covers workloads not used during training.

Queue-age metrics still describe samples from the ready queue; they are not completed-process total waiting times. The current MLFQ implementation also needs to become distinct from Round Robin before that baseline comparison is meaningful.
