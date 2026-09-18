"""
scheduler_algorithms.py — Round Robin, Priority Scheduling, and MLFQ as
complete, standalone, run-to-completion functions.

Pure OS coursework logic. Zero knowledge of RL, Gym, or Claude — every
function here can be tested in isolation with a plain list of Process
objects.
"""

import copy

from process import Process, generate_sample_processes


def _reset_processes(processes):
    """Deep-copies the input list so running the same processes through
    multiple algorithms in one script doesn't leak mutated state between
    runs."""
    return copy.deepcopy(processes)


def _summarize(completed_processes):
    if not completed_processes:
        return {"avg_wait_time": 0.0, "max_wait_time": 0.0, "completed": []}
    wait_times = [p.waiting_time for p in completed_processes]
    return {
        "avg_wait_time": sum(wait_times) / len(wait_times),
        "max_wait_time": max(wait_times),
        "completed": completed_processes,
    }


def simulate_round_robin(processes, quantum=2, verbose=False):
    processes = _reset_processes(processes)
    pending = sorted(processes, key=lambda p: p.arrival_time)
    ready_queue = []
    completed = []
    time = 0

    def admit_arrivals():
        while pending and pending[0].arrival_time <= time:
            proc = pending.pop(0)
            proc.last_ready_time = time
            ready_queue.append(proc)

    admit_arrivals()

    while ready_queue or pending:
        if not ready_queue:
            # CPU idle until the next arrival
            time = pending[0].arrival_time
            admit_arrivals()
            continue

        current = ready_queue.pop(0)
        slice_len = min(quantum, current.remaining_time)
        if verbose:
            print(f"t={time}: running {current.pid} for {slice_len} ticks")
        time += slice_len
        current.remaining_time -= slice_len

        # New arrivals during this slice join the ready queue before the
        # process that just ran (so it doesn't cut the line on itself).
        admit_arrivals()

        if current.is_finished():
            current.completion_time = time
            current.waiting_time = (
                current.completion_time - current.arrival_time - current.burst_time
            )
            completed.append(current)
            if verbose:
                print(f"t={time}: {current.pid} completed, wait={current.waiting_time}")
        else:
            current.last_ready_time = time
            ready_queue.append(current)

    return _summarize(completed)


def simulate_priority_scheduling(processes, verbose=False):
    """Non-preemptive: always run the ready process with the lowest
    priority number to completion. Intentionally does NOT prevent
    starvation of low-priority processes — that's a deliberate gap the
    RL agent is meant to later notice and fix via apply_action(4)."""
    processes = _reset_processes(processes)
    pending = sorted(processes, key=lambda p: p.arrival_time)
    ready_queue = []
    completed = []
    time = 0

    def admit_arrivals():
        while pending and pending[0].arrival_time <= time:
            proc = pending.pop(0)
            proc.last_ready_time = time
            ready_queue.append(proc)

    admit_arrivals()

    while ready_queue or pending:
        if not ready_queue:
            time = pending[0].arrival_time
            admit_arrivals()
            continue

        ready_queue.sort(key=lambda p: p.priority)
        current = ready_queue.pop(0)
        if verbose:
            print(f"t={time}: running {current.pid} (priority={current.priority}) to completion")
        time += current.remaining_time
        current.remaining_time = 0
        current.completion_time = time
        current.waiting_time = (
            current.completion_time - current.arrival_time - current.burst_time
        )
        completed.append(current)
        admit_arrivals()
        if verbose:
            print(f"t={time}: {current.pid} completed, wait={current.waiting_time}")

    return _summarize(completed)


def simulate_mlfq(processes, quantums=(2, 4, 8), verbose=False):
    """Multiple queues, one per entry in quantums (index 0 = fastest /
    shortest quantum). New arrivals enter level 0. Always run from the
    lowest non-empty level first. A process that doesn't finish within
    its current level's quantum is demoted (capped at the last level)."""
    processes = _reset_processes(processes)
    pending = sorted(processes, key=lambda p: p.arrival_time)
    levels = [[] for _ in quantums]
    completed = []
    time = 0

    def admit_arrivals():
        while pending and pending[0].arrival_time <= time:
            proc = pending.pop(0)
            proc.last_ready_time = time
            levels[0].append(proc)

    admit_arrivals()

    def any_ready():
        return any(levels)

    while any_ready() or pending:
        if not any_ready():
            time = pending[0].arrival_time
            admit_arrivals()
            continue

        level_idx = next(i for i, q in enumerate(levels) if q)
        current = levels[level_idx].pop(0)
        quantum = quantums[level_idx]
        slice_len = min(quantum, current.remaining_time)
        if verbose:
            print(f"t={time}: running {current.pid} at level {level_idx} for {slice_len} ticks")
        time += slice_len
        current.remaining_time -= slice_len

        admit_arrivals()

        if current.is_finished():
            current.completion_time = time
            current.waiting_time = (
                current.completion_time - current.arrival_time - current.burst_time
            )
            completed.append(current)
            if verbose:
                print(f"t={time}: {current.pid} completed, wait={current.waiting_time}")
        else:
            current.last_ready_time = time
            next_level = min(level_idx + 1, len(levels) - 1)
            levels[next_level].append(current)

    return _summarize(completed)


if __name__ == "__main__":
    for name, fn in [
        ("Round Robin", simulate_round_robin),
        ("Priority Scheduling", simulate_priority_scheduling),
        ("MLFQ", simulate_mlfq),
    ]:
        print(f"\n=== {name} ===")
        result = fn(generate_sample_processes(), verbose=True)
        print(f"avg_wait_time={result['avg_wait_time']:.2f} max_wait_time={result['max_wait_time']}")
