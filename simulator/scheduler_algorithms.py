"""Standalone, deterministic implementations of the simulator policies."""

import copy
import heapq

from process import Process, generate_sample_processes


DEFAULT_MLFQ_QUANTUMS = (2, 4, 8)
DEFAULT_MLFQ_BOOST_INTERVAL = 50


def _reset_processes(processes):
    """Deep-copy inputs so independent policy runs do not share mutations."""
    return copy.deepcopy(processes)


def _validate_positive_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _summarize(completed_processes):
    if not completed_processes:
        return {
            "avg_wait_time": 0.0,
            "max_wait_time": 0.0,
            "avg_response_time": 0.0,
            "avg_turnaround_time": 0.0,
            "completed": [],
        }
    wait_times = [process.waiting_time for process in completed_processes]
    response_times = [process.response_time for process in completed_processes]
    turnaround_times = [process.turnaround_time for process in completed_processes]
    return {
        "avg_wait_time": sum(wait_times) / len(wait_times),
        "max_wait_time": max(wait_times),
        "avg_response_time": sum(response_times) / len(response_times),
        "avg_turnaround_time": sum(turnaround_times) / len(turnaround_times),
        "completed": completed_processes,
    }


def _validate_mlfq(quantums, boost_interval):
    try:
        quantums = tuple(quantums)
    except TypeError as exc:
        raise ValueError("quantums must be a non-empty iterable") from exc
    if not quantums:
        raise ValueError("quantums must contain at least one level")
    for quantum in quantums:
        _validate_positive_integer("each MLFQ quantum", quantum)
    _validate_positive_integer("boost_interval", boost_interval)
    return quantums


def _simulate(processes, policy, quantum=2, quantums=DEFAULT_MLFQ_QUANTUMS,
              boost_interval=DEFAULT_MLFQ_BOOST_INTERVAL, verbose=False):
    processes = _reset_processes(processes)
    pending = sorted(processes, key=lambda process: process.arrival_time)
    ready = [] if policy != "mlfq" else None
    levels = [[] for _ in quantums] if policy == "mlfq" else None
    blocked = []
    event_sequence = 0
    completed = []
    time = 0

    def enqueue(process, level=0):
        if policy == "mlfq":
            levels[min(level, len(levels) - 1)].append(process)
        else:
            ready.append(process)

    def process_events_through(limit):
        """At a timestamp, arrivals precede simultaneous I/O completions."""
        while True:
            next_arrival = pending[0].arrival_time if pending else None
            next_wakeup = blocked[0][0] if blocked else None
            candidates = [
                event_time for event_time in (next_arrival, next_wakeup)
                if event_time is not None and event_time <= limit
            ]
            if not candidates:
                return
            event_time = min(candidates)
            while pending and pending[0].arrival_time <= event_time:
                process = pending.pop(0)
                process.mark_ready(process.arrival_time)
                enqueue(process, 0)
            due = []
            while blocked and blocked[0][0] <= event_time:
                due.append(heapq.heappop(blocked))
            for wake_time, sequence, process, level in due:
                process.complete_io(wake_time)
                enqueue(process, level if level is not None else 0)

    def any_ready():
        return any(levels) if policy == "mlfq" else bool(ready)

    def pop_ready():
        if policy == "mlfq":
            level = next(index for index, queue in enumerate(levels) if queue)
            return levels[level].pop(0), level
        if policy == "priority":
            # Stable ordering makes equal priorities deterministic.
            ready.sort(key=lambda process: process.priority)
        return ready.pop(0), None

    def boost_ready(current=None):
        boosted = [process for queue in levels for process in queue]
        for queue in levels:
            queue.clear()
        for process in boosted:
            process.add_waiting_time(time - process.last_ready_time)
            process.last_ready_time = time
            levels[0].append(process)
        if current is not None:
            current.last_ready_time = time
            current.transition_to(Process.READY)
            levels[0].append(current)

    process_events_through(time)
    while any_ready() or pending or blocked:
        if not any_ready():
            next_arrival = pending[0].arrival_time if pending else None
            next_wakeup = blocked[0][0] if blocked else None
            time = min(value for value in (next_arrival, next_wakeup) if value is not None)
            process_events_through(time)
            continue

        current, level = pop_ready()
        current.add_waiting_time(time - current.last_ready_time)
        current.start(time)
        until_io = current.cpu_time_until_io()
        if policy == "rr":
            duration = min(quantum, current.remaining_time)
        elif policy == "priority":
            duration = current.remaining_time
        else:
            until_boost = boost_interval - (time % boost_interval)
            duration = min(quantums[level], current.remaining_time, until_boost)
        if until_io is not None:
            duration = min(duration, until_io)

        if verbose:
            if policy == "mlfq":
                print(f"t={time}: running {current.pid} at MLFQ level {level} for {duration}")
            else:
                print(f"t={time}: running {current.pid} for {duration} ticks")
        current.execute_cpu(duration, time)
        time += duration

        # Arrivals and completed I/O are queued before the running process is
        # blocked or requeued at this boundary.
        process_events_through(time)
        io_due = current.cpu_time_until_io() == 0
        if io_due:
            wake_time = current.request_io(time)
            heapq.heappush(
                blocked, (wake_time, event_sequence, current, level)
            )
            event_sequence += 1
        elif current.is_finished():
            completed.append(current)
        elif policy == "mlfq" and time % boost_interval == 0:
            boost_ready(current)
        elif policy == "mlfq":
            current.last_ready_time = time
            current.transition_to(Process.READY)
            levels[min(level + 1, len(levels) - 1)].append(current)
        elif policy == "rr":
            current.last_ready_time = time
            current.transition_to(Process.READY)
            ready.append(current)

        # Priority scheduling is non-preemptive between CPU and I/O events.
        # If it blocked, it is absent from all ready queues until wake-up.
        if policy == "mlfq" and time % boost_interval == 0 and (io_due or current.is_finished()):
            boost_ready()

    return _summarize(completed)


def simulate_round_robin(processes, quantum=2, verbose=False):
    """Round Robin with non-preempting arrivals and I/O requests."""
    _validate_positive_integer("quantum", quantum)
    return _simulate(processes, "rr", quantum=quantum, verbose=verbose)


def simulate_priority_scheduling(processes, verbose=False):
    """Non-preemptive Priority; a running process yields only for I/O."""
    return _simulate(processes, "priority", verbose=verbose)


def simulate_mlfq(
    processes,
    quantums=DEFAULT_MLFQ_QUANTUMS,
    verbose=False,
    boost_interval=DEFAULT_MLFQ_BOOST_INTERVAL,
):
    """MLFQ with FIFO levels, quantum demotion, and periodic global boosts.

    I/O wakeups return to the level from which the process blocked. A request
    reached at a quantum boundary blocks before quantum demotion is applied.
    """
    quantums = _validate_mlfq(quantums, boost_interval)
    return _simulate(
        processes,
        "mlfq",
        quantums=quantums,
        boost_interval=boost_interval,
        verbose=verbose,
    )


if __name__ == "__main__":
    for name, algorithm in (
        ("Round Robin", simulate_round_robin),
        ("Priority Scheduling", simulate_priority_scheduling),
        ("MLFQ", simulate_mlfq),
    ):
        print(f"\n=== {name} ===")
        result = algorithm(generate_sample_processes(), verbose=True)
        print(
            f"avg_wait_time={result['avg_wait_time']:.2f} "
            f"max_wait_time={result['max_wait_time']}"
        )
